from pathlib import Path
from dotenv import load_dotenv

# Load .env if present (no-op when file is absent)
load_dotenv(Path(__file__).parent / ".env", override=False)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"
DB_PATH  = DATA_DIR / "news.db"

# ── Feed ───────────────────────────────────────────────────────────────────────
INDIA_FEED_URL = (
    "https://news.google.com/rss/headlines/section/geo/India"
    "?hl=en-IN&gl=IN&ceid=IN:en"
)

# How many cluster articles to keep per story (0 = all)
MAX_CLUSTER_ARTICLES = 0

# ── Export ────────────────────────────────────────────────────────────────────
# Directory where scraped story stubs are written (relative to repo root).
# Point this at your Astro content/stories/ folder or set to DATA_DIR.
EXPORT_DIR = BASE_DIR.parent / "content" / "stories" / "scraped"

# Keep stories fetched within this many days in the export
EXPORT_DAYS_WINDOW = 3

# ── HTTP ──────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 15  # seconds
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; Raspberry Pi) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)

# ── LLM ──────────────────────────────────────────────────────────────────────
import os

# Model string passed to litellm.completion — any provider litellm supports.
# Set the corresponding API key env var (e.g. GEMINI_API_KEY, OPENAI_API_KEY).
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "gemini/gemini-2.0-flash")

# How many hours back to search when expanding a story's article list
ARTICLE_EXPAND_HOURS = int(os.getenv("ARTICLE_EXPAND_HOURS", "48"))

# ── Article selection ─────────────────────────────────────────────────────────
# Target number of representative articles to keep after expansion
ARTICLE_SELECT_COUNT = int(os.getenv("ARTICLE_SELECT_COUNT", "25"))
# Maximum articles from the same publisher in the selected set
ARTICLE_SOURCE_CAP = int(os.getenv("ARTICLE_SOURCE_CAP", "3"))

# ── Dashboard ─────────────────────────────────────────────────────────────────

DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
# Set a strong random value in production: python -c "import secrets; print(secrets.token_hex(32))"
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "change-me-in-production")
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "changeme")

# ── Telegram bot ──────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Comma-separated list of allowed Telegram user IDs (leave empty to allow all)
TELEGRAM_ALLOWED_USERS = [
    int(x) for x in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if x.strip()
]
