"""
JSON exporter.

Reads recent stories from the DB and writes one JSON file per story into
EXPORT_DIR using the same schema the Astro frontend expects (stub format —
neutral summary and left/right perspectives are placeholders until an LLM
enrichment step fills them in).

Output file: <EXPORT_DIR>/<slug>.json
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import EXPORT_DAYS_WINDOW, EXPORT_DIR
from storage.db import get_session
from storage.models import Article, Story

logger = logging.getLogger(__name__)


def _story_to_dict(story: Story) -> dict:
    articles = sorted(story.articles, key=lambda a: a.position)
    sources = [
        {
            "name": a.source_name or "Unknown",
            "url": a.url,
            "title": a.title,
            "isLead": a.is_lead,
        }
        for a in articles
    ]

    return {
        "slug": story.slug,
        "title": story.headline,
        "topic": "India",
        "publishedAt": story.published_at.isoformat(),
        "fetchedAt": story.fetched_at.isoformat(),
        "primarySource": story.primary_source,
        "sources": sources,
        # Placeholder fields — to be enriched by a subsequent LLM step
        "neutral": {"summary": ""},
        "left":    {"take": "", "quotes": []},
        "right":   {"take": "", "quotes": []},
    }


def export_recent(days: int = EXPORT_DAYS_WINDOW) -> int:
    """
    Write JSON stubs for all stories fetched within the last `days` days.
    Returns the number of files written.
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with get_session() as session:
        stories = (
            session.execute(
                select(Story)
                .options(selectinload(Story.articles))
                .where(Story.fetched_at >= cutoff)
                .order_by(Story.published_at.desc())
            )
            .scalars()
            .all()
        )

        written = 0
        for story in stories:
            data = _story_to_dict(story)
            path = EXPORT_DIR / f"{story.slug}.json"
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            written += 1

    logger.info("Exported %d story files to %s", written, EXPORT_DIR)
    return written
