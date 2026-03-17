"""
Database engine and session management.

Usage:
    from storage.db import get_session, init_db

    init_db()               # run once at startup (creates tables if missing)

    with get_session() as session:
        session.add(some_model)
        # commits automatically on __exit__; rolls back on exception
"""

from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from config import DB_PATH
from storage.models import Base

# Build the SQLite URL; ensure the data directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable WAL mode for better concurrent read performance on RPi SD card
@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


def _migrate() -> None:
    """Add new columns to existing tables if they are absent (SQLite ALTER TABLE)."""
    with _engine.connect() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(stories)"))
        }
        migrations = [
            ("image_url",  "TEXT"),
            ("image_path", "VARCHAR"),
        ]
        for col, col_type in migrations:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE stories ADD COLUMN {col} {col_type}"))
        conn.commit()

    with _engine.connect() as conn:
        existing_art = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(articles)"))
        }
        article_migrations = [
            ("resolved_url", "TEXT"),
            ("image_path",   "VARCHAR"),
        ]
        for col, col_type in article_migrations:
            if col not in existing_art:
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {col} {col_type}"))
        conn.commit()


def init_db() -> None:
    """Create all tables and apply lightweight column migrations."""
    Base.metadata.create_all(_engine)
    _migrate()


@contextmanager
def get_session():
    """Yields a SQLAlchemy Session that auto-commits or rolls back."""
    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
