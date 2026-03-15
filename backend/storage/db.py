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

from sqlalchemy import create_engine, event
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


def init_db() -> None:
    """Create all tables (idempotent — safe to call every startup)."""
    Base.metadata.create_all(_engine)


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
