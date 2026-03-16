"""
Feed entry parser.

Converts a raw feedparser entry into structured Python dicts ready for
storage.  All messy extraction logic (HTML description parsing, headline
cleaning, slug generation) lives here — keeping models and fetcher clean.

Returned shape per entry
────────────────────────
{
    "guid":           str,          # RSS guid — dedup key
    "headline":       str,          # cleaned headline (no " - Source" suffix)
    "slug":           str,          # url-safe slug
    "primary_source": str | None,
    "published_at":   datetime,
    "articles": [
        {
            "title":       str,
            "url":         str,
            "source_name": str | None,
            "position":    int,
            "is_lead":     bool,
        },
        ...
    ]
}
"""

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

from config import MAX_CLUSTER_ARTICLES

logger = logging.getLogger(__name__)

# ── Slug generation ────────────────────────────────────────────────────────────

_SLUG_STRIP = re.compile(r"[^\w\s-]")
_SLUG_SPACES = re.compile(r"[\s_]+")


def _to_slug(text: str) -> str:
    text = text.lower()
    text = _SLUG_STRIP.sub("", text)
    text = _SLUG_SPACES.sub("-", text).strip("-")
    return text[:80]  # cap length


# ── Headline cleaning ──────────────────────────────────────────────────────────

def _clean_headline(raw: str, source: str | None) -> str:
    """Remove the trailing ' - Source Name' from an RSS title."""
    if source:
        suffix = f" - {source}"
        if raw.endswith(suffix):
            return raw[: -len(suffix)].strip()
    # Fallback: strip the last ' - ...' segment
    cleaned = re.sub(r"\s+-\s+[^-]+$", "", raw)
    return cleaned.strip()


# ── Description HTML parser ────────────────────────────────────────────────────

class _DescriptionParser(HTMLParser):
    """
    Parses the <description> field of a Google News RSS item.

    Google encodes clusters as an HTML <ol> where each <li> contains an <a>
    (article title + URL) followed by a <font> tag with the source name.

    Example fragment (unescaped):
        <ol>
          <li>
            <a href="...">Article headline</a>&nbsp;&nbsp;
            <font color="#6f6f6f">Source Name</font>
          </li>
        </ol>
    """

    def __init__(self):
        super().__init__()
        self.articles: list[dict] = []
        self._in_a = False
        self._in_font = False
        self._current: dict | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr_dict = dict(attrs)
        if tag == "a":
            self._current = {"title": "", "url": attr_dict.get("href", ""), "source_name": None}
            self._in_a = True
        elif tag == "font":
            self._in_font = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_a = False
        elif tag == "font":
            self._in_font = False
        elif tag == "li" and self._current:
            self.articles.append(self._current)
            self._current = None

    def handle_data(self, data: str) -> None:
        if not self._current:
            return
        if self._in_a:
            self._current["title"] += data
        elif self._in_font:
            self._current["source_name"] = data.strip()


def _parse_description(html: str) -> list[dict]:
    """Return a list of article dicts from the description HTML."""
    parser = _DescriptionParser()
    parser.feed(html)
    return parser.articles


# ── Published date ─────────────────────────────────────────────────────────────

def _parse_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_entries(entries: list) -> list[dict]:
    """
    Convert a list of feedparser entries into structured story dicts.
    Skips entries that cannot be parsed (logged as warnings).
    """
    stories = []

    for entry in entries:
        try:
            stories.append(_parse_entry(entry))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping entry %r: %s", entry.get("id", "?"), exc)

    return stories


def parse_search_entries(entries: list) -> list[dict]:
    """
    Parse entries from a Google News RSS *search* result feed.

    Search feed entries are individual articles (not clusters), so the
    structure is simpler: title, link, and source.title.

    Returns a list of article dicts:
        {"title": str, "url": str, "source_name": str | None}
    """
    articles = []
    for entry in entries:
        try:
            raw_title: str = entry.get("title", "").strip()
            url: str = entry.get("link", "").strip()
            if not url:
                continue
            # Strip trailing " - Source Name" from the title
            title = re.sub(r"\s+-\s+[^-]+$", "", raw_title).strip()
            src = entry.get("source") or {}
            source_name: str | None = src.get("title") or None
            articles.append({"title": title, "url": url, "source_name": source_name})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping search entry: %s", exc)
    return articles


def _parse_entry(entry) -> dict:
    guid = entry.get("id") or entry.get("link") or ""
    if not guid:
        raise ValueError("Entry has no guid or link")

    primary_source: str | None = None
    src = entry.get("source")
    if src:
        primary_source = src.get("title") or src.get("href")

    raw_title: str = entry.get("title", "").strip()
    headline = _clean_headline(raw_title, primary_source)
    slug = _to_slug(headline)

    published_at = _parse_date(entry.get("published"))

    # Parse cluster articles from the description HTML
    description_html: str = entry.get("description", "")
    raw_articles = _parse_description(description_html)

    # Cap at configured limit (0 = keep all)
    if MAX_CLUSTER_ARTICLES:
        raw_articles = raw_articles[:MAX_CLUSTER_ARTICLES]

    articles = []
    for pos, art in enumerate(raw_articles):
        articles.append(
            {
                "title": art["title"].strip(),
                "url": art["url"],
                "source_name": art.get("source_name"),
                "position": pos,
                "is_lead": pos == 0,
            }
        )

    return {
        "guid": guid,
        "headline": headline,
        "slug": slug,
        "primary_source": primary_source,
        "published_at": published_at,
        "articles": articles,
    }
