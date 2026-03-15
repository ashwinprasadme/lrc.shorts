"""
Tests for scraper/parser.py — pure unit tests, no DB, no network.
"""

from datetime import timezone

import pytest

from scraper.parser import _clean_headline, _to_slug, _parse_description, parse_entries

# ── Headline cleaning ─────────────────────────────────────────────────────────

def test_clean_headline_strips_source():
    assert _clean_headline("Budget announced - The Hindu", "The Hindu") == "Budget announced"


def test_clean_headline_fallback_strips_last_segment():
    assert _clean_headline("Big story - NDTV", None) == "Big story"


def test_clean_headline_no_source_suffix():
    # When title doesn't match the pattern, return as-is
    result = _clean_headline("Just a headline", "NDTV")
    assert result == "Just a headline"


def test_clean_headline_multiple_dashes():
    # Only the LAST ' - Source' segment is stripped
    result = _clean_headline("Delhi-Mumbai rail link - Times of India", "Times of India")
    assert result == "Delhi-Mumbai rail link"


# ── Slug generation ───────────────────────────────────────────────────────────

def test_slug_lowercase_and_hyphens():
    assert _to_slug("Budget Announced 2026") == "budget-announced-2026"


def test_slug_strips_special_chars():
    slug = _to_slug("India's GDP grows 7%!")
    assert "'" not in slug
    assert "%" not in slug
    assert "!" not in slug


def test_slug_max_length():
    long = "a " * 50
    assert len(_to_slug(long)) <= 80


# ── Description HTML parser ───────────────────────────────────────────────────

SAMPLE_DESCRIPTION = """
<ol>
  <li>
    <a href="https://example.com/article1">Election dates announced</a>&nbsp;&nbsp;
    <font color="#6f6f6f">The Hindu</font>
  </li>
  <li>
    <a href="https://example.com/article2">Polls scheduled for 4 states</a>&nbsp;&nbsp;
    <font color="#6f6f6f">NDTV</font>
  </li>
  <li>
    <a href="https://example.com/article3">EC press conference today</a>&nbsp;&nbsp;
    <font color="#6f6f6f">Times of India</font>
  </li>
</ol>
"""


def test_description_parser_count():
    articles = _parse_description(SAMPLE_DESCRIPTION)
    assert len(articles) == 3


def test_description_parser_first_article():
    articles = _parse_description(SAMPLE_DESCRIPTION)
    assert articles[0]["title"] == "Election dates announced"
    assert articles[0]["url"] == "https://example.com/article1"
    assert articles[0]["source_name"] == "The Hindu"


def test_description_parser_all_sources():
    articles = _parse_description(SAMPLE_DESCRIPTION)
    sources = [a["source_name"] for a in articles]
    assert sources == ["The Hindu", "NDTV", "Times of India"]


def test_description_parser_empty():
    assert _parse_description("") == []


def test_description_parser_no_font():
    html = '<ol><li><a href="https://x.com">Title only</a></li></ol>'
    articles = _parse_description(html)
    assert len(articles) == 1
    assert articles[0]["title"] == "Title only"
    assert articles[0]["source_name"] is None


# ── parse_entries ─────────────────────────────────────────────────────────────

def _make_entry(guid="test-guid-1", title="Test story - NDTV", source="NDTV",
                published="Sun, 15 Mar 2026 08:00:00 GMT", description=SAMPLE_DESCRIPTION):
    """Build a minimal feedparser-like entry dict."""
    class FakeSource:
        def get(self, k, d=None):
            return {"title": source, "href": f"https://{source.lower()}.com"}.get(k, d)

    entry = {
        "id": guid,
        "title": title,
        "source": {"title": source},
        "published": published,
        "description": description,
    }
    return entry


def test_parse_entries_basic():
    entries = [_make_entry()]
    results = parse_entries(entries)
    assert len(results) == 1
    s = results[0]
    assert s["headline"] == "Test story"
    assert s["primary_source"] == "NDTV"
    assert s["guid"] == "test-guid-1"
    assert len(s["articles"]) == 3


def test_parse_entries_lead_article():
    results = parse_entries([_make_entry()])
    articles = results[0]["articles"]
    assert articles[0]["is_lead"] is True
    assert all(not a["is_lead"] for a in articles[1:])


def test_parse_entries_positions():
    results = parse_entries([_make_entry()])
    positions = [a["position"] for a in results[0]["articles"]]
    assert positions == [0, 1, 2]


def test_parse_entries_published_at_timezone():
    results = parse_entries([_make_entry()])
    dt = results[0]["published_at"]
    assert dt.tzinfo is not None


def test_parse_entries_skip_bad_entry():
    entries = [{"id": "", "title": "", "source": {}, "published": None, "description": ""}]
    # Entry with no guid — should be skipped, not raise
    results = parse_entries(entries)
    assert results == []


def test_parse_entries_multiple():
    entries = [
        _make_entry(guid="g1", title="Story one - NDTV"),
        _make_entry(guid="g2", title="Story two - The Hindu", source="The Hindu"),
    ]
    results = parse_entries(entries)
    assert len(results) == 2
    assert results[0]["slug"] != results[1]["slug"]
