"""
Scraper entry point - designed to be run as a one-shot process.
Schedule this via systemd timer or cron; it runs, exits, done.

Usage
-----
    python main.py           # fetch, store, export, exit
    python main.py --dry-run # fetch and parse only, no DB writes
"""

import argparse
import logging
import sys
from datetime import datetime

from config import LOG_DIR
from exporter import export_recent
from scraper.fetcher import fetch_feed
from scraper.parser import parse_entries
from storage.db import init_db
from storage.ingestion import ingest

# Logging

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_scrape(dry_run: bool = False) -> None:
    start = datetime.now()
    logger.info("Scrape started at %s", start.strftime("%Y-%m-%d %H:%M:%S"))

    entries = fetch_feed()
    stories = parse_entries(entries)

    if dry_run:
        logger.info("Dry run -- %d stories parsed, nothing written", len(stories))
        for s in stories[:5]:
            logger.info("  %s (%d articles)", s["headline"], len(s["articles"]))
        return

    new, skipped = ingest(stories)
    exported = export_recent()

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(
        "Done -- %d new | %d skipped | %d exported  (%.1fs)",
        new, skipped, exported, elapsed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="LRC News Shorts -- India news scraper")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse feed without writing to DB or exporting files",
    )
    args = parser.parse_args()

    init_db()
    run_scrape(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
