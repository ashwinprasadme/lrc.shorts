"""
Story ingestion — write parsed story dicts into the database.

Key behaviour
─────────────
- New stories are inserted; already-seen guids are skipped entirely
  (one SELECT per batch via a NOT IN query, not N individual lookups).
- Slug collisions (rare, two very similar headlines) get a numeric suffix.
- Returns counts of new vs skipped stories for logging.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from storage.db import get_session
from storage.models import Article, Story

logger = logging.getLogger(__name__)


def _unique_slug(base_slug: str, session) -> str:
    """Append a counter suffix if base_slug already exists in the DB."""
    slug = base_slug
    counter = 1
    existing = {
        row[0]
        for row in session.execute(
            select(Story.slug).where(Story.slug.like(f"{base_slug}%"))
        )
    }
    while slug in existing:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def ingest(stories: list[dict]) -> tuple[int, int]:
    """
    Persist a list of parsed story dicts to the database.

    Returns (new_count, skipped_count).
    """
    if not stories:
        return 0, 0

    all_guids = [s["guid"] for s in stories]

    with get_session() as session:
        # Bulk-fetch all guids we've already seen — single query
        existing_guids: set[str] = {
            row[0]
            for row in session.execute(
                select(Story.guid).where(Story.guid.in_(all_guids))
            )
        }

        new_count = 0
        skipped_count = 0

        for story_data in stories:
            guid = story_data["guid"]

            if guid in existing_guids:
                skipped_count += 1
                continue

            slug = _unique_slug(story_data["slug"], session)

            story = Story(
                guid=guid,
                headline=story_data["headline"],
                slug=slug,
                primary_source=story_data.get("primary_source"),
                published_at=story_data["published_at"],
                fetched_at=datetime.now(timezone.utc),
            )
            session.add(story)
            # Flush to get story.id before adding child articles
            session.flush()

            for art in story_data.get("articles", []):
                article = Article(
                    story_id=story.id,
                    title=art["title"],
                    url=art["url"],
                    source_name=art.get("source_name"),
                    position=art["position"],
                    is_lead=art["is_lead"],
                )
                session.add(article)

            new_count += 1

        logger.info("Ingested %d new stories, skipped %d duplicates", new_count, skipped_count)
        return new_count, skipped_count


def expand_story_articles(
    story_id: int, articles: list[dict], start_position: int = 0
) -> int:
    """
    Add new articles to an existing story, skipping any URL already stored
    for that story (checked in bulk before insert).

    Each dict in `articles` must have at minimum: title, url.
    Optional keys: source_name.

    Returns the count of articles actually inserted.
    """
    if not articles:
        return 0

    urls = [a["url"] for a in articles]

    with get_session() as session:
        # Bulk-fetch URLs already present for this story — single query
        existing_urls: set[str] = {
            row[0]
            for row in session.execute(
                select(Article.url).where(
                    Article.story_id == story_id,
                    Article.url.in_(urls),
                )
            )
        }

        added = 0
        for art in articles:
            if art["url"] in existing_urls:
                continue
            session.add(
                Article(
                    story_id=story_id,
                    title=art["title"],
                    url=art["url"],
                    source_name=art.get("source_name"),
                    position=start_position + added,
                    is_lead=False,
                )
            )
            added += 1

        logger.info("Added %d new articles to story %d", added, story_id)
        return added
