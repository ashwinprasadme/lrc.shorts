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

    Stores the remote image URL from the RSS feed (if present) but does NOT
    download the image.  Call fetch_article_images() on demand or via the
    expand pipeline.

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
                # Store the remote URL so it's available for on-demand download
                image_url=story_data.get("image_url"),
            )
            session.add(story)
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


def fetch_article_images(slug: str, max_articles: int = 5) -> list[dict]:
    """
    Download featured images for the first *max_articles* articles of a story.

    Skips articles that already have a locally cached image.  Writes back
    ``image_path`` and ``resolved_url`` for each article that is processed.

    Returns a list of result dicts with keys:
        article_id, position, image_url, filename, resolved_url.
    """
    from scraper.image_fetcher import download_article_image  # noqa: PLC0415

    with get_session() as session:
        story_id_row = session.execute(
            select(Story.id).where(Story.slug == slug)
        ).one_or_none()
        if story_id_row is None:
            raise ValueError(f"Story not found: {slug!r}")
        story_id = story_id_row[0]

        article_rows = session.execute(
            select(Article.id, Article.url, Article.position, Article.image_path)
            .where(Article.story_id == story_id)
            .order_by(Article.position)
            .limit(max_articles)
        ).all()

    results = []
    for article_id, url, position, existing_path in article_rows:
        if existing_path:
            logger.debug(
                "Article image already cached for story %r pos=%d", slug, position
            )
            results.append({
                "article_id": article_id,
                "position": position,
                "filename": existing_path,
                "image_url": None,
                "resolved_url": None,
            })
            continue

        image_url, filename, resolved_url, body_text = download_article_image(
            slug, position, url
        )

        with get_session() as session:
            article = session.get(Article, article_id)
            if article:
                if filename:
                    article.image_path = filename
                if resolved_url and not article.resolved_url:
                    article.resolved_url = resolved_url
                if body_text and not article.body_text:
                    article.body_text = body_text

        results.append({
            "article_id": article_id,
            "position": position,
            "image_url": image_url,
            "filename": filename,
            "resolved_url": resolved_url,
            "body_text": body_text,
        })

    logger.info(
        "Fetched article images for %r: %d saved of %d processed",
        slug,
        sum(1 for r in results if r.get("filename")),
        len(results),
    )
    return results


def generate_story_featured_image(slug: str) -> dict:
    """
    Generate an AI featured image for the story using the OpenAI Images API.

    Collects article titles and any locally-cached article images, builds the
    styled prompt from ``scraper/image_gen_prompt.md``, calls the generator,
    and persists the resulting filename to ``Story.image_path``.

    Returns a dict with keys: filename, image_url, ref_images_used.
    Raises ValueError if the story does not exist.
    """
    from pathlib import Path  # noqa: PLC0415

    from config import IMAGES_DIR  # noqa: PLC0415
    from scraper.image_generator import generate_featured_image  # noqa: PLC0415

    with get_session() as session:
        story_row = session.execute(
            select(Story.id, Story.slug).where(Story.slug == slug)
        ).one_or_none()
        if story_row is None:
            raise ValueError(f"Story not found: {slug!r}")
        story_id, story_slug = story_row

        article_rows = session.execute(
            select(Article.title, Article.image_path)
            .where(Article.story_id == story_id)
            .order_by(Article.position)
        ).all()

    headlines = [row.title for row in article_rows]
    ref_paths: list[Path] = [
        IMAGES_DIR / row.image_path
        for row in article_rows
        if row.image_path
    ]

    filename, image_url = generate_featured_image(story_slug, headlines, ref_paths)

    if filename:
        with get_session() as session:
            story = session.execute(
                select(Story).where(Story.slug == slug)
            ).scalar_one()
            story.image_path = filename
            if image_url:
                story.image_url = image_url

    return {
        "filename": filename,
        "image_url": image_url,
        "ref_images_used": len([p for p in ref_paths if p.exists()]),
    }


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
