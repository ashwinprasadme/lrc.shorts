"""
Tests for exporter.py — JSON file output and schema.
"""

import json
from datetime import datetime, timezone

import pytest

from exporter import export_recent
from storage.ingestion import ingest


def _story(guid="g1", slug="test-story", headline="Test Headline"):
    return {
        "guid": guid,
        "headline": headline,
        "slug": slug,
        "primary_source": "NDTV",
        "published_at": datetime(2026, 3, 15, 8, 0, 0, tzinfo=timezone.utc),
        "articles": [
            {"title": "Primary", "url": "https://ndtv.com/a", "source_name": "NDTV",
             "position": 0, "is_lead": True},
            {"title": "Secondary", "url": "https://hindu.com/a", "source_name": "The Hindu",
             "position": 1, "is_lead": False},
        ],
    }


def test_export_creates_file(tmp_db):
    ingest([_story()])
    count = export_recent(days=7)
    assert count == 1
    export_dir = tmp_db["export_dir"]
    files = list(export_dir.glob("*.json"))
    assert len(files) == 1


def test_export_filename_matches_slug(tmp_db):
    ingest([_story(slug="my-test-slug")])
    export_recent(days=7)
    export_dir = tmp_db["export_dir"]
    assert (export_dir / "my-test-slug.json").exists()


def test_export_json_schema(tmp_db):
    ingest([_story()])
    export_recent(days=7)
    export_dir = tmp_db["export_dir"]
    data = json.loads((export_dir / "test-story.json").read_text())

    assert data["slug"] == "test-story"
    assert data["title"] == "Test Headline"
    assert data["topic"] == "India"
    assert data["primarySource"] == "NDTV"
    assert "publishedAt" in data
    assert "fetchedAt" in data
    assert isinstance(data["sources"], list)
    # Placeholder fields present
    assert "neutral" in data
    assert "left" in data
    assert "right" in data


def test_export_sources_shape(tmp_db):
    ingest([_story()])
    export_recent(days=7)
    export_dir = tmp_db["export_dir"]
    data = json.loads((export_dir / "test-story.json").read_text())

    sources = data["sources"]
    assert len(sources) == 2
    lead = next(s for s in sources if s["isLead"])
    assert lead["name"] == "NDTV"
    assert lead["url"] == "https://ndtv.com/a"


def test_export_multiple_stories(tmp_db):
    ingest([
        _story(guid="g1", slug="story-one", headline="Story One"),
        _story(guid="g2", slug="story-two", headline="Story Two"),
    ])
    count = export_recent(days=7)
    assert count == 2
    export_dir = tmp_db["export_dir"]
    assert (export_dir / "story-one.json").exists()
    assert (export_dir / "story-two.json").exists()


def test_export_empty_db(tmp_db):
    count = export_recent(days=7)
    assert count == 0
