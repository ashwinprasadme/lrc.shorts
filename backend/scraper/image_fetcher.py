"""
Featured-image fetcher.

Uses a long-running Playwright (Chromium) browser session to:
  1. Navigate to the lead article URL, following all redirects (including
     Google News redirect chains) with JavaScript executing normally.
  2. Handle consent / cookie popups automatically.
  3. Extract the featured image using a publisher-specific extractor class
     (falling back to og:image then first in-body image for unknown sites).
  4. Download that image URL via requests and convert to JPEG at
     JPEG_QUALITY % quality with Pillow.

The browser is lazy-initialised on first use and kept alive across calls.
A module-level lock makes it safe to call from multiple threads.

Publisher customisation
───────────────────────
Add a subclass of ``BaseExtractor`` below and register it in
``_EXTRACTOR_REGISTRY`` mapping a hostname substring to an instance.

Public function
───────────────
    download_article_image(story_slug, position, article_url)
        -> (image_url | None, filename | None, resolved_url | None)
"""

import atexit
import io
import logging
import threading
from urllib.parse import urlparse

import requests

from config import IMAGES_DIR, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

JPEG_QUALITY = 90
_HEADERS = {"User-Agent": USER_AGENT}

# ── Long-running Playwright browser session ────────────────────────────────────

_pw = None       # playwright instance
_browser = None  # Chromium browser
_browser_lock = threading.Lock()


def _get_browser():
    """Return a shared Chromium browser, launching it if not already running."""
    global _pw, _browser

    with _browser_lock:
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "playwright is not installed. "
                "Run: pip install playwright && playwright install chromium"
            ) from exc

        if _browser is None or not _browser.is_connected():
            # Clean up any stale instance
            for obj in (_browser, _pw):
                if obj is not None:
                    try:
                        obj.close() if hasattr(obj, "close") else obj.stop()
                    except Exception:  # noqa: BLE001
                        pass

            _pw = sync_playwright().start()
            _browser = _pw.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            logger.info("Playwright Chromium browser started")

    return _browser


def _shutdown_browser() -> None:
    global _pw, _browser
    with _browser_lock:
        for obj, method in ((_browser, "close"), (_pw, "stop")):
            if obj is not None:
                try:
                    getattr(obj, method)()
                except Exception:  # noqa: BLE001
                    pass
        _browser = None
        _pw = None
    logger.debug("Playwright browser shut down")


atexit.register(_shutdown_browser)


# ── Publisher-specific extractor classes ──────────────────────────────────────

class BaseExtractor:
    """
    Base class for publisher-specific featured-image extractors.

    Sub-classes should override ``get_image_url`` and optionally
    ``handle_consent``.  Both receive a fully-loaded Playwright ``Page``
    object.
    """

    def handle_consent(self, page) -> None:
        """Click through any consent / cookie popups.  No-op by default."""

    def get_image_url(self, page) -> str | None:
        """Return an absolute image URL from the rendered page, or None."""
        raise NotImplementedError


class DefaultExtractor(BaseExtractor):
    """
    Generic extractor used for unknown publishers.

    Strategy (in order):
      1. Common consent-button selectors (OneTrust, Google consent, generic).
      2. og:image meta tag.
      3. First <img> inside common article-body container selectors.
    """

    # Consent button text / selectors (tried in order; stops at first click)
    _CONSENT_BUTTONS = [
        # Google's own consent interstitial (consent.google.com)
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        # OneTrust
        "#onetrust-accept-btn-handler",
        ".onetrust-accept-btn-handler",
        # Generic
        'button:has-text("Accept All")',
        'button:has-text("Accept")',
        'button:has-text("Agree")',
        'button:has-text("Continue")',
        '[aria-label*="Accept"]',
        '[data-testid*="accept"]',
    ]

    # CSS selectors for article-body image, tried in order
    _ARTICLE_IMG_SELECTORS = [
        "article img",
        '[itemprop="articleBody"] img',
        '[class*="article-body"] img',
        '[class*="article_body"] img',
        '[class*="story-body"] img',
        '[class*="story_body"] img',
        '[class*="article-content"] img',
        '[class*="article_content"] img',
        '[class*="entry-content"] img',
        "main article img",
        "main .content img",
        "main img",
    ]

    def handle_consent(self, page) -> None:
        for sel in self._CONSENT_BUTTONS:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1_500):
                    btn.click()
                    logger.debug("Clicked consent button: %s", sel)
                    page.wait_for_load_state("networkidle", timeout=4_000)
                    return
            except Exception:  # noqa: BLE001
                pass

    def get_image_url(self, page) -> str | None:
        # 1. og:image (fastest, most reliable when present)
        og = page.get_attribute('meta[property="og:image"]', "content")
        if not og:
            og = page.get_attribute('meta[name="og:image"]', "content")
        if og:
            return og

        # 2. First significant image in article body
        for sel in self._ARTICLE_IMG_SELECTORS:
            try:
                loc = page.locator(sel).first
                src = loc.get_attribute("src", timeout=1_000)
                if not src:
                    src = loc.get_attribute("data-src", timeout=500)
                if src and src.startswith(("http://", "https://")):
                    return src
            except Exception:  # noqa: BLE001
                pass

        return None


# ── Publisher-specific overrides ──────────────────────────────────────────────

class TheHinduExtractor(DefaultExtractor):
    """thehindu.com — featured image sits in .picture-big or .lead-img."""

    def get_image_url(self, page) -> str | None:
        for sel in ('[class*="picture-big"] img', '[class*="lead-img"] img',
                    '.article-image img', '.lead-img img'):
            try:
                src = page.locator(sel).first.get_attribute("src", timeout=1_000)
                if src and src.startswith(("http://", "https://")):
                    return src
            except Exception:  # noqa: BLE001
                pass
        return super().get_image_url(page)


class NDTVExtractor(DefaultExtractor):
    """ndtv.com — featured image is in .ins_storybody or .story__thumbnail."""

    def get_image_url(self, page) -> str | None:
        for sel in ('.story__thumbnail img', '.ins_storybody img',
                    '[class*="article_img"] img'):
            try:
                src = page.locator(sel).first.get_attribute("src", timeout=1_000)
                if src and src.startswith(("http://", "https://")):
                    return src
            except Exception:  # noqa: BLE001
                pass
        return super().get_image_url(page)


class TimesOfIndiaExtractor(DefaultExtractor):
    """timesofindia.indiatimes.com — image in ._2lD-Z or .I7_MQ wrapper."""

    def get_image_url(self, page) -> str | None:
        for sel in ('figure.I7_MQ img', '[class*="_2lD-Z"] img',
                    '.article_img img', 'figure img'):
            try:
                src = page.locator(sel).first.get_attribute("src", timeout=1_000)
                if src and src.startswith(("http://", "https://")):
                    return src
            except Exception:  # noqa: BLE001
                pass
        return super().get_image_url(page)


class HindustanTimesExtractor(DefaultExtractor):
    """hindustantimes.com — image in .storyPage-imageWrap or .detail-image."""

    def get_image_url(self, page) -> str | None:
        for sel in ('.storyPage-imageWrap img', '.detail-image img',
                    '[class*="storyDetailImage"] img'):
            try:
                src = page.locator(sel).first.get_attribute("src", timeout=1_000)
                if src and src.startswith(("http://", "https://")):
                    return src
            except Exception:  # noqa: BLE001
                pass
        return super().get_image_url(page)


class IndianExpressExtractor(DefaultExtractor):
    """indianexpress.com — image in .custom-caption or .ie-first-publish."""

    def get_image_url(self, page) -> str | None:
        for sel in ('.custom-caption img', '[class*="featured-image"] img',
                    '.story-element-image img', 'span.ie-first-publish img'):
            try:
                src = page.locator(sel).first.get_attribute("src", timeout=1_000)
                if src and src.startswith(("http://", "https://")):
                    return src
            except Exception:  # noqa: BLE001
                pass
        return super().get_image_url(page)


# ── Extractor registry ────────────────────────────────────────────────────────
# Maps a hostname substring to an extractor instance.
# Entries are checked in order; the first match wins.
# The sentinel "" entry at the end handles all unknown publishers.

_EXTRACTOR_REGISTRY: list[tuple[str, BaseExtractor]] = [
    ("thehindu.com",              TheHinduExtractor()),
    ("ndtv.com",                  NDTVExtractor()),
    ("timesofindia.indiatimes.com", TimesOfIndiaExtractor()),
    ("hindustantimes.com",        HindustanTimesExtractor()),
    ("indianexpress.com",         IndianExpressExtractor()),
    ("",                          DefaultExtractor()),   # catch-all — keep last
]

_default_extractor = DefaultExtractor()


def _extractor_for(url: str) -> BaseExtractor:
    """Return the best extractor for the given article URL."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return _default_extractor
    for pattern, extractor in _EXTRACTOR_REGISTRY:
        if not pattern or pattern in host:
            return extractor
    return _default_extractor


# ── Core browser fetch ────────────────────────────────────────────────────────

def _fetch_image_and_resolved_url(
    article_url: str,
) -> tuple[str | None, str | None]:
    """
    Open *article_url* in a fresh browser context, handle consent popups,
    then extract the featured image URL.

    Returns ``(image_url, resolved_url)`` where *resolved_url* is the final
    URL after all redirects (e.g. the decoded destination of a Google News
    link).  Either value may be ``None`` on failure.
    """
    try:
        browser = _get_browser()
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            java_script_enabled=True,
        )
        page = ctx.new_page()
        try:
            page.goto(
                article_url,
                wait_until="domcontentloaded",
                timeout=REQUEST_TIMEOUT * 1_000,
            )

            # Capture the final URL after all redirects
            resolved_url: str | None = page.url or None

            # Determine which extractor to use based on the resolved hostname
            extractor = _extractor_for(resolved_url or article_url)

            # Handle consent / cookie popups
            extractor.handle_consent(page)

            # Extract featured image
            image_url = extractor.get_image_url(page)
            return image_url, resolved_url

        finally:
            page.close()
            ctx.close()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Browser fetch failed for %s: %s", article_url, exc)
        return None, None


# ── Public API ─────────────────────────────────────────────────────────────────

def download_article_image(
    story_slug: str,
    position: int,
    article_url: str,
) -> tuple[str | None, str | None, str | None]:
    """
    Fetch and locally cache the featured image for a single article.

    Uses the publisher-specific extractor for *article_url*, handles consent
    popups, and saves the image as ``{story_slug}-{position}.jpg`` in
    ``IMAGES_DIR``.

    Returns ``(image_url, filename, resolved_url)`` — all ``None`` on failure.
    """
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("Pillow is not installed. Run: pip install Pillow") from exc

    image_url, resolved_url = _fetch_image_and_resolved_url(article_url)

    if not image_url:
        logger.debug(
            "No featured image found for story %r pos=%d", story_slug, position
        )
        return None, None, resolved_url

    if not image_url.startswith(("http://", "https://")):
        logger.warning(
            "Ignoring non-HTTP image URL for story %r pos=%d: %.120s",
            story_slug, position, image_url,
        )
        return None, None, resolved_url

    filename = f"{story_slug}-{position}.jpg"
    dest = IMAGES_DIR / filename

    try:
        resp = requests.get(
            image_url,
            headers=_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            logger.warning(
                "Unexpected Content-Type %r for story %r pos=%d; skipping",
                content_type, story_slug, position,
            )
            return image_url, None, resolved_url

        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True)
        logger.info(
            "Saved article image for %r pos=%d → %s", story_slug, position, filename
        )
        return image_url, filename, resolved_url

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to save article image for story %r pos=%d: %s",
            story_slug, position, exc,
        )
        return image_url, None, resolved_url
