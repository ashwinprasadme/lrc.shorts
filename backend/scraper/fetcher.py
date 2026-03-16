"""
RSS fetcher.

Fetches the Google News India feed and returns a list of raw parsed entries
from feedparser. Handles transient network errors with a simple retry.
"""

import logging
import time
import urllib.parse

import feedparser

from config import INDIA_FEED_URL, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

# feedparser reads User-Agent from this module-level attribute
feedparser.USER_AGENT = USER_AGENT


def fetch_feed(url: str = INDIA_FEED_URL, retries: int = 3) -> list:
    """
    Fetch and parse a Google News RSS feed.

    Returns a list of feedparser entry objects.
    Raises RuntimeError if all retries are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            logger.info("Fetching feed (attempt %d): %s", attempt, url)
            feed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})

            # feedparser swallows HTTP errors; check bozo flag and status
            if feed.get("bozo") and not feed.entries:
                raise ValueError(
                    f"Feed parse error: {feed.get('bozo_exception', 'unknown')}"
                )

            status = feed.get("status", 200)
            if status >= 400:
                raise ValueError(f"HTTP {status} from feed URL")

            logger.info("Fetched %d entries from feed", len(feed.entries))
            return feed.entries

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Attempt %d failed: %s", attempt, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential back-off: 2s, 4s

    raise RuntimeError(
        f"All {retries} attempts to fetch feed failed"
    ) from last_exc


def fetch_search_articles(query: str, when_hours: int = 48) -> list:
    """
    Search Google News RSS for articles matching `query` published within
    the last `when_hours` hours.

    The `when:Nh` operator is appended to the query automatically.  Google
    News RSS supports h (hours), d (days), m (months).

    Returns raw feedparser entry objects.
    """
    full_query = f"{query} when:{when_hours}h"
    q = urllib.parse.quote_plus(full_query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    logger.info("Searching RSS: %s", full_query)
    return fetch_feed(url)
