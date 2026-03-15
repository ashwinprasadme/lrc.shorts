"""
Flask dashboard — stats, story browser, and basic auth.

Run:
    python dashboard/app.py

Or via gunicorn for production:
    gunicorn -w 1 -b 0.0.0.0:5000 'dashboard.app:create_app()'
"""

import sys
from pathlib import Path

# Allow imports from backend root when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from config import (
    DASHBOARD_PASSWORD,
    DASHBOARD_SECRET_KEY,
    DASHBOARD_USERNAME,
)
from storage.db import get_session, init_db
from storage.models import Article, Story


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.secret_key = DASHBOARD_SECRET_KEY

    # Pre-hash the password once at startup
    _pw_hash = generate_password_hash(DASHBOARD_PASSWORD)

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("authenticated"):
                return redirect(url_for("login", next=request.path))
            return f(*args, **kwargs)
        return decorated

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if username == DASHBOARD_USERNAME and check_password_hash(_pw_hash, password):
                session["authenticated"] = True
                session.permanent = True
                return redirect(request.args.get("next") or url_for("index"))
            error = "Invalid credentials"
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        # Subquery: article count per story
        article_count_sq = (
            select(func.count(Article.id))
            .where(Article.story_id == Story.id)
            .correlate(Story)
            .scalar_subquery()
        )

        with get_session() as db:
            total_stories = db.execute(select(func.count(Story.id))).scalar()
            total_articles = db.execute(select(func.count(Article.id))).scalar()
            stories_today = db.execute(
                select(func.count(Story.id)).where(Story.fetched_at >= today_start)
            ).scalar()
            stories_week = db.execute(
                select(func.count(Story.id)).where(Story.fetched_at >= week_start)
            ).scalar()
            latest_fetch = db.execute(select(func.max(Story.fetched_at))).scalar()

            top_sources = db.execute(
                select(Article.source_name, func.count(Article.id).label("n"))
                .where(Article.source_name.isnot(None))
                .group_by(Article.source_name)
                .order_by(func.count(Article.id).desc())
                .limit(10)
            ).all()

            # Plain dicts — no lazy loading, safe outside session
            rows = db.execute(
                select(
                    Story.id, Story.slug, Story.headline,
                    Story.primary_source, Story.published_at,
                    article_count_sq.label("article_count"),
                )
                .order_by(Story.published_at.desc())
                .limit(50)
            ).mappings().all()
            recent_stories = [dict(r) for r in rows]

        stats = {
            "total_stories": total_stories,
            "total_articles": total_articles,
            "stories_today": stories_today,
            "stories_week": stories_week,
            "latest_fetch": latest_fetch,
            "top_sources": top_sources,
        }
        return render_template("index.html", stats=stats, stories=recent_stories)

    @app.route("/story/<slug>")
    @login_required
    def story_detail(slug: str):
        with get_session() as db:
            story_row = db.execute(
                select(
                    Story.slug, Story.headline, Story.primary_source,
                    Story.published_at, Story.fetched_at,
                )
                .where(Story.slug == slug)
            ).mappings().one_or_none()
            if story_row is None:
                return "Story not found", 404
            story = dict(story_row)

            articles = db.execute(
                select(
                    Article.title, Article.url,
                    Article.source_name, Article.position, Article.is_lead,
                )
                .join(Story, Article.story_id == Story.id)
                .where(Story.slug == slug)
                .order_by(Article.position)
            ).mappings().all()
            articles = [dict(a) for a in articles]
        return render_template("story.html", story=story, articles=articles)

    @app.route("/search")
    @login_required
    def search():
        q = request.args.get("q", "").strip()
        results = []
        if q:
            pattern = f"%{q}%"
            article_count_sq = (
                select(func.count(Article.id))
                .where(Article.story_id == Story.id)
                .correlate(Story)
                .scalar_subquery()
            )
            with get_session() as db:
                rows = db.execute(
                    select(
                        Story.id, Story.slug, Story.headline,
                        Story.primary_source, Story.published_at,
                        article_count_sq.label("article_count"),
                    )
                    .where(Story.headline.ilike(pattern))
                    .order_by(Story.published_at.desc())
                    .limit(30)
                ).mappings().all()
                results = [dict(r) for r in rows]
        return render_template("search.html", results=results, query=q)

    return app


if __name__ == "__main__":
    import sys
    from config import DASHBOARD_HOST, DASHBOARD_PORT

    init_db()
    app = create_app()
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)
