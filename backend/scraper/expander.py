"""
Story article expander.

For each recently-ingested story, this module:
  1. Builds a focused Google News RSS search query using an LLM
     (scraper.query_builder.build_search_query).
  2. Fetches matching articles published within the last ARTICLE_EXPAND_HOURS
     hours via the Google News RSS search endpoint.
  3. Parses the search result entries into article dicts.
  4. Merges them into the story's article list, skipping duplicates by URL.

Entry point:  expand_recent_stories(since)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import ARTICLE_EXPAND_HOURS, ARTICLE_SELECT_COUNT, ARTICLE_SOURCE_CAP
from scraper.fetcher import fetch_search_articles
from scraper.parser import parse_search_entries
from scraper.query_builder import build_search_query
from scraper.selector import select_articles
from storage.db import get_session
from storage.ingestion import expand_story_articles, fetch_article_images
from storage.models import Story

logger = logging.getLogger(__name__)


def expand_story_by_slug(slug: str) -> int:
    """
    Expand article list for a single story identified by slug, then
    download the featured image if one hasn't been cached yet.

    Returns the number of new articles added, or raises ValueError if the
    slug is not found.
    """
    with get_session() as session:
        story = (
            session.execute(
                select(Story)
                .options(selectinload(Story.articles))
                .where(Story.slug == slug)
            )
            .scalar_one_or_none()
        )

    if story is None:
        raise ValueError(f"Story not found: {slug!r}")

    added = _expand_one(story)
    if added:
        logger.info("+%d articles → %s", added, story.slug)

    try:
        fetch_article_images(slug)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Article image fetch failed for %r during expand: %s", slug, exc)

    return added


def expand_recent_stories(since: datetime) -> int:
    """
    Expand article lists for all stories first fetched at or after `since`.

    Each story gets one LLM call (to build the query) and one RSS fetch.
    Articles already present (matched by URL) are silently skipped.

    Returns the total number of new articles added across all stories.
    """
    with get_session() as session:
        stories = (
            session.execute(
                select(Story)
                .options(selectinload(Story.articles))
                .where(Story.fetched_at >= since)
                .order_by(Story.published_at.desc())
            )
            .scalars()
            .all()
        )

    if not stories:
        logger.info("No new stories to expand")
        return 0

    logger.info("Expanding articles for %d new stories", len(stories))
    total_added = 0

    for story in stories:
        try:
            added = _expand_one(story)
            total_added += added
            if added:
                logger.info("  +%d articles → %s", added, story.slug)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Expansion failed for %r: %s", story.slug, exc)
            continue

        try:
            fetch_article_images(story.slug)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Article image fetch failed for %r: %s", story.slug, exc)

    return total_added


def _expand_one(story: Story) -> int:
    """Expand a single story's article list. Returns count of new articles added."""
    article_titles = [a.title for a in story.articles]

    # Step 1 — LLM builds a focused query from the story context
    query = build_search_query(story.headline, article_titles)

    # Step 2 — Fetch matching articles from Google News RSS search
    entries = fetch_search_articles(query, when_hours=ARTICLE_EXPAND_HOURS)

    # Step 3 — Parse search entries (individual articles, not clusters)
    candidates = parse_search_entries(entries)

    # Step 4 — Build full combined pool (existing + fresh), run selection
    existing_urls = {a.url for a in story.articles}
    existing_as_dicts = [
        {
            "title": a.title,
            "url": a.url,
            "source_name": a.source_name,
            "position": a.position,
            "is_lead": a.is_lead,
        }
        for a in story.articles
    ]
    pool = existing_as_dicts + [a for a in candidates if a["url"] not in existing_urls]

    # Step 5 — Select representative articles, then persist only net-new ones
    selected = select_articles(
        articles=pool,
        story_headline=story.headline,
        target=ARTICLE_SELECT_COUNT,
        source_cap=ARTICLE_SOURCE_CAP,
    )
    to_add = [a for a in selected if a["url"] not in existing_urls]

    if not to_add:
        return 0

    return expand_story_articles(
        story_id=story.id,
        articles=to_add,
        start_position=len(story.articles),
    )
