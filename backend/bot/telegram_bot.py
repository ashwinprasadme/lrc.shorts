"""
Telegram bot — management interface for the news backend.

Commands
--------
/start | /help    — list all commands
/stats            — DB counts and last fetch time
/list [n]         — latest n story headlines (default 10, max 20)
/search <query>   — search headlines
/story <slug>     — full story detail with all sources
/sources          — top 10 sources by article count

Run:
    python bot/telegram_bot.py

Requires TELEGRAM_BOT_TOKEN in environment or config.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_ALLOWED_USERS, TELEGRAM_BOT_TOKEN
from scraper.expander import expand_recent_stories
from storage.db import get_session, init_db
from storage.models import Article, Story

from sqlalchemy import func, select

logger = logging.getLogger(__name__)


# ── Auth guard ────────────────────────────────────────────────────────────────

def _allowed(update: Update) -> bool:
    if not TELEGRAM_ALLOWED_USERS:
        return True  # open to anyone if no allowlist configured
    return update.effective_user.id in TELEGRAM_ALLOWED_USERS


async def _deny(update: Update) -> None:
    await update.message.reply_text("Sorry, you are not authorised to use this bot.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%d %b %Y %H:%M UTC")


def _truncate(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return await _deny(update)
    text = (
        "*LRC News Shorts — Bot*\n\n"
        "/stats — DB summary\n"
        "/list \\[n\\] — latest n stories \\(default 10\\)\n"
        "/search \\<query\\> — search headlines\n"
        "/story \\<slug\\> — story detail \\+ all sources\n"
        "/sources — top 10 source outlets\n"
        "/expand \\[hours\\] — expand articles for recent stories \\(default 24h\\)\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return await _deny(update)

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week = datetime.now(timezone.utc) - timedelta(days=7)

    with get_session() as db:
        total_s = db.execute(select(func.count(Story.id))).scalar()
        total_a = db.execute(select(func.count(Article.id))).scalar()
        today_s = db.execute(
            select(func.count(Story.id)).where(Story.fetched_at >= today)
        ).scalar()
        week_s = db.execute(
            select(func.count(Story.id)).where(Story.fetched_at >= week)
        ).scalar()
        last_fetch = db.execute(select(func.max(Story.fetched_at))).scalar()

    text = (
        f"*Database stats*\n\n"
        f"Stories total: `{total_s}`\n"
        f"Articles total: `{total_a}`\n"
        f"Stories today: `{today_s}`\n"
        f"Stories this week: `{week_s}`\n"
        f"Last fetch: `{_fmt_dt(last_fetch)}`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return await _deny(update)

    n = 10
    if context.args:
        try:
            n = min(int(context.args[0]), 20)
        except ValueError:
            pass

    with get_session() as db:
        stories = (
            db.execute(
                select(Story).order_by(Story.published_at.desc()).limit(n)
            )
            .scalars()
            .all()
        )

    if not stories:
        await update.message.reply_text("No stories in the database yet.")
        return

    lines = [f"*Latest {len(stories)} stories*\n"]
    for i, s in enumerate(stories, 1):
        pub = s.published_at.strftime("%d %b %H:%M") if s.published_at else "?"
        headline = s.headline.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`").replace("[", "\\[")
        slug = s.slug.replace("-", "\\-").replace(".", "\\.")
        lines.append(f"{i}\\. [{headline}]() `{pub}` — /story\\_{slug[:30]}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return await _deny(update)

    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return

    query = " ".join(context.args)
    pattern = f"%{query}%"

    with get_session() as db:
        stories = (
            db.execute(
                select(Story)
                .where(Story.headline.ilike(pattern))
                .order_by(Story.published_at.desc())
                .limit(10)
            )
            .scalars()
            .all()
        )

    if not stories:
        await update.message.reply_text(f'No results for "{query}".')
        return

    lines = [f"*Search: {query}*\n"]
    for i, s in enumerate(stories, 1):
        pub = s.published_at.strftime("%d %b %H:%M") if s.published_at else "?"
        headline = s.headline.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`").replace("[", "\\[")
        lines.append(f"{i}\\. {headline} \\(`{pub}`\\)")
        lines.append(f"   `/story_{s.slug[:40]}`")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_story(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return await _deny(update)

    # Command is /story_<slug> (Telegram command friendly) or /story <slug>
    slug = None
    if context.args:
        slug = context.args[0].lstrip("/")
    else:
        # Try parsing slug from command name e.g. /story_some-headline
        cmd = update.message.text.split()[0].lstrip("/")
        if "_" in cmd:
            slug = cmd.split("_", 1)[1]

    if not slug:
        await update.message.reply_text("Usage: /story <slug>")
        return

    with get_session() as db:
        story = db.execute(
            select(Story).where(Story.slug == slug)
        ).scalar_one_or_none()

        if story is None:
            # Partial match fallback
            story = db.execute(
                select(Story).where(Story.slug.ilike(f"{slug}%")).limit(1)
            ).scalar_one_or_none()

        if story is None:
            await update.message.reply_text(f'Story not found: "{slug}"')
            return

        articles = sorted(story.articles, key=lambda a: a.position)

    pub = _fmt_dt(story.published_at)
    headline = story.headline.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
    source = (story.primary_source or "Unknown").replace(".", "\\.").replace("-", "\\-")

    lines = [
        f"*{headline}*",
        f"Source: {source} \\| `{pub}`\n",
        f"*Coverage \\({len(articles)} outlets\\):*",
    ]
    for a in articles:
        sname = (a.source_name or "Unknown").replace(".", "\\.").replace("-", "\\-").replace("(", "\\(").replace(")", "\\)")
        title = _truncate(a.title, 80).replace("*", "\\*").replace("_", "\\_").replace("`", "\\`").replace("[", "\\[").replace("]", "\\]")
        lead = " \\[lead\\]" if a.is_lead else ""
        lines.append(f"• {sname}{lead}: {title}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return await _deny(update)

    with get_session() as db:
        rows = db.execute(
            select(Article.source_name, func.count(Article.id).label("n"))
            .where(Article.source_name.isnot(None))
            .group_by(Article.source_name)
            .order_by(func.count(Article.id).desc())
            .limit(10)
        ).all()

    if not rows:
        await update.message.reply_text("No source data yet.")
        return

    lines = ["*Top 10 sources*\n"]
    for i, (name, count) in enumerate(rows, 1):
        name_esc = (name or "Unknown").replace(".", "\\.").replace("-", "\\-").replace("(", "\\(").replace(")", "\\)").replace("&", "\\&")
        lines.append(f"{i}\\. {name_esc} — `{count}`")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_expand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return await _deny(update)

    hours = 24
    if context.args:
        try:
            hours = max(1, min(int(context.args[0]), 168))
        except ValueError:
            await update.message.reply_text("Usage: /expand [hours] (1–168)")
            return

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    await update.message.reply_text(f"Expanding articles for stories from the last {hours}h… this may take a moment.")

    added = expand_recent_stories(since=since)

    await update.message.reply_text(f"Done\. `+{added}` articles added\." , parse_mode=ParseMode.MARKDOWN_V2)


# ── Bot startup ───────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set. Configure it in .env or environment.")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )

    init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("story", cmd_story))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("expand", cmd_expand))

    logger.info("Bot started. Polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
