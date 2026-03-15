"""
Tests for storage/ingestion.py — deduplication, slug collision, article insertion.
"""

from datetime import datetime, timezone

import pytest

from storage.db import get_session
from storage.ingestion import ingest
from storage.models import Article, Story
from sqlalchemy import select


def _story(guid="g1", headline="Test Headline", slug="test-headline",
           source="NDTV", articles=None):
    if articles is None:
        articles = [
            {"title": "Primary article", "url": "https://ndtv.com/a", "source_name": "NDTV", "position": 0, "is_lead": True},
            {"title": "Secondary", "url": "https://hindu.com/a", "source_name": "The Hindu", "position": 1, "is_lead": False},
        ]
    return {
        "guid": guid,
        "headline": headline,
        "slug": slug,
        "primary_source": source,
        "published_at": datetime(2026, 3, 15, 8, 0, 0, tzinfo=timezone.utc),
        "articles": articles,
    }


def test_ingest_new_story(tmp_db):
    new, skipped = ingest([_story()])
    assert new == 1
    assert skipped == 0


def test_ingest_story_persisted(tmp_db):
    ingest([_story()])
    with get_session() as db:
        story = db.execute(select(Story).where(Story.guid == "g1")).scalar_one()
        assert story.headline == "Test Headline"
        assert story.primary_source == "NDTV"


def test_ingest_articles_persisted(tmp_db):
    ingest([_story()])
    with get_session() as db:
        articles = db.execute(
            select(Article).join(Story).where(Story.guid == "g1")
            .order_by(Article.position)
        ).scalars().all()
    assert len(articles) == 2
    assert articles[0].is_lead is True
    assert articles[0].source_name == "NDTV"
    assert articles[1].is_lead is False


def test_ingest_deduplication(tmp_db):
    ingest([_story()])
    new, skipped = ingest([_story()])  # same guid
    assert new == 0
    assert skipped == 1


def test_ingest_bulk_dedup(tmp_db):
    stories = [_story(guid=f"g{i}", slug=f"slug-{i}", headline=f"Headline {i}") for i in range(10)]
    ingest(stories)
    # Re-ingest same batch — all should be skipped
    new, skipped = ingest(stories)
    assert new == 0
    assert skipped == 10


def test_ingest_mixed_new_and_duplicate(tmp_db):
    ingest([_story(guid="g1", slug="slug-1", headline="Story 1")])
    new, skipped = ingest([
        _story(guid="g1", slug="slug-1", headline="Story 1"),  # dup
        _story(guid="g2", slug="slug-2", headline="Story 2"),  # new
    ])
    assert new == 1
    assert skipped == 1


def test_ingest_slug_collision_gets_suffix(tmp_db):
    ingest([_story(guid="g1", slug="test-slug", headline="Story One")])
    # Different guid but same slug
    new, _ = ingest([_story(guid="g2", slug="test-slug", headline="Story Two")])
    assert new == 1
    with get_session() as db:
        stories = db.execute(select(Story).order_by(Story.id)).scalars().all()
    slugs = [s.slug for s in stories]
    assert len(set(slugs)) == 2  # both unique


def test_ingest_empty_list(tmp_db):
    new, skipped = ingest([])
    assert new == 0
    assert skipped == 0


def test_ingest_story_without_articles(tmp_db):
    # Should not error even with empty articles list
    new, skipped = ingest([_story(articles=[])])
    assert new == 1
