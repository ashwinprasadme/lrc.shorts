"""
Tests for scraper/expander.py.

All external I/O (LLM query builder, RSS fetch, RSS parsing) is mocked so
the tests are fast and network-free; the DB layer runs against the in-memory
SQLite instance provided by the `tmp_db` fixture.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from scraper.expander import _expand_one, expand_recent_stories
from storage.db import get_session
from storage.ingestion import ingest
from storage.models import Article, Story

# A fixed point in the past — stories ingested during the test will have
# fetched_at ≈ now (2026-03-15), so passing this as `since` picks them up.
_SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)
# A point in the far future so no currently-ingested story qualifies.
_FUTURE = datetime(2030, 1, 1, tzinfo=timezone.utc)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _story_data(guid="g1", headline="Test Headline", slug="test-headline"):
    return {
        "guid": guid,
        "headline": headline,
        "slug": slug,
        "primary_source": "NDTV",
        "published_at": datetime(2026, 3, 15, 8, 0, 0, tzinfo=timezone.utc),
        "articles": [
            {
                "title": "Lead article",
                "url": "https://ndtv.com/original",
                "source_name": "NDTV",
                "position": 0,
                "is_lead": True,
            }
        ],
    }


def _candidates(*urls):
    """Build a list of parsed-article dicts with the given URLs."""
    return [
        {"title": f"New article {i}", "url": url, "source_name": "The Hindu"}
        for i, url in enumerate(urls)
    ]


def _load_story(guid: str) -> Story:
    """Fetch a Story (with articles eagerly loaded) from the test DB."""
    with get_session() as db:
        return db.execute(
            select(Story)
            .options(selectinload(Story.articles))
            .where(Story.guid == guid)
        ).scalar_one()


# ── expand_recent_stories ─────────────────────────────────────────────────────


def test_no_stories_returns_zero(tmp_db):
    """Returns 0 when the database holds no stories."""
    assert expand_recent_stories(since=_SINCE) == 0


def test_since_filters_out_older_stories(tmp_db):
    """Stories ingested before `since` are ignored."""
    ingest([_story_data()])

    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://new.com/1")),
    ):
        assert expand_recent_stories(since=_FUTURE) == 0


def test_new_articles_are_counted(tmp_db):
    """Returns the number of articles added for a single story."""
    ingest([_story_data()])

    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://new.com/1")),
    ):
        assert expand_recent_stories(since=_SINCE) == 1


def test_duplicate_urls_not_counted(tmp_db):
    """An article URL already in the story is silently skipped."""
    ingest([_story_data()])

    # Same URL as the existing lead article
    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://ndtv.com/original")),
    ):
        assert expand_recent_stories(since=_SINCE) == 0


def test_no_candidates_returns_zero(tmp_db):
    """Returns 0 when the RSS search yields no articles."""
    ingest([_story_data()])

    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=[]),
    ):
        assert expand_recent_stories(since=_SINCE) == 0


def test_multiple_stories_totalled(tmp_db):
    """New articles across multiple stories are summed."""
    ingest([
        _story_data(guid="g1", slug="story-one"),
        _story_data(guid="g2", slug="story-two"),
    ])

    # Each story gets one fresh article
    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://new.com/x")),
    ):
        assert expand_recent_stories(since=_SINCE) == 2


def test_per_story_failure_does_not_abort_remaining(tmp_db):
    """An exception in one story's expansion is caught; the rest still run."""
    ingest([
        _story_data(guid="g1", slug="story-fail"),
        _story_data(guid="g2", slug="story-ok"),
    ])

    call_count = 0

    def _flaky(headline, titles):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("LLM unavailable")
        return "good query"

    with (
        patch("scraper.expander.build_search_query", side_effect=_flaky),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://new.com/1")),
    ):
        result = expand_recent_stories(since=_SINCE)

    # Exactly one story succeeded
    assert result == 1


def test_articles_are_persisted_to_db(tmp_db):
    """Expanded articles actually appear in the database."""
    ingest([_story_data()])

    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://new.com/persisted")),
    ):
        expand_recent_stories(since=_SINCE)

    with get_session() as db:
        story = db.execute(select(Story).where(Story.guid == "g1")).scalar_one()
        articles = db.execute(
            select(Article).where(Article.story_id == story.id)
        ).scalars().all()

    urls = {a.url for a in articles}
    assert "https://new.com/persisted" in urls


# ── _expand_one ───────────────────────────────────────────────────────────────


def test_expand_one_returns_count(tmp_db):
    """_expand_one returns the number of newly added articles."""
    ingest([_story_data()])
    story = _load_story("g1")

    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://new.com/a")),
    ):
        assert _expand_one(story) == 1


def test_expand_one_deduplicates_against_existing(tmp_db):
    """Only URLs not already in story.articles are inserted."""
    ingest([_story_data()])
    story = _load_story("g1")

    candidates = _candidates(
        "https://ndtv.com/original",   # already in story
        "https://thehindu.com/new",    # genuinely new
    )

    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=candidates),
    ):
        assert _expand_one(story) == 1


def test_expand_one_all_duplicates_returns_zero(tmp_db):
    """Returns 0 when every candidate URL is already present."""
    ingest([_story_data()])
    story = _load_story("g1")

    with (
        patch("scraper.expander.build_search_query", return_value="q"),
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=_candidates("https://ndtv.com/original")),
    ):
        assert _expand_one(story) == 0


def test_expand_one_uses_headline_for_query(tmp_db):
    """build_search_query is called with the story's headline."""
    ingest([_story_data(headline="Special Headline")])
    story = _load_story("g1")

    with (
        patch("scraper.expander.build_search_query", return_value="q") as mock_bsq,
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=[]),
    ):
        _expand_one(story)

    mock_bsq.assert_called_once()
    assert mock_bsq.call_args[0][0] == "Special Headline"


def test_expand_one_passes_article_titles_to_query_builder(tmp_db):
    """Existing article titles are forwarded to build_search_query."""
    ingest([_story_data()])
    story = _load_story("g1")

    with (
        patch("scraper.expander.build_search_query", return_value="q") as mock_bsq,
        patch("scraper.expander.fetch_search_articles", return_value=[]),
        patch("scraper.expander.parse_search_entries", return_value=[]),
    ):
        _expand_one(story)

    titles_arg = mock_bsq.call_args[0][1]
    assert "Lead article" in titles_arg
