"""
Shared pytest fixtures.

Uses an in-memory SQLite DB for every test — fast, isolated, no disk cleanup needed.
Overrides config paths so nothing touches real data directories.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend root is on sys.path when running from repo root
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


# ── Override config before any backend module is imported ────────────────────

os.environ.setdefault("DASHBOARD_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "testpass")


@pytest.fixture(scope="function")
def tmp_db(tmp_path, monkeypatch):
    """
    Patch DB_PATH and EXPORT_DIR to temp locations so every test
    gets a fresh, isolated database and export directory.
    """
    import config as cfg

    db_file = tmp_path / "test_news.db"
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    monkeypatch.setattr(cfg, "DB_PATH", db_file)
    monkeypatch.setattr(cfg, "EXPORT_DIR", export_dir)

    # Also patch names already imported into other modules
    import exporter
    monkeypatch.setattr(exporter, "EXPORT_DIR", export_dir)

    # Re-create the engine pointing at the temp DB
    import storage.db as db_mod
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from storage.models import Base

    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _):
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.close()

    Base.metadata.create_all(engine)

    monkeypatch.setattr(db_mod, "_engine", engine)
    monkeypatch.setattr(
        db_mod, "_SessionFactory",
        sessionmaker(bind=engine, expire_on_commit=False),
    )

    return {"db_path": db_file, "export_dir": export_dir, "engine": engine}


@pytest.fixture(scope="function")
def flask_client(tmp_db):
    """Flask test client with a fresh DB."""
    from dashboard.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def _login(client):
    """Helper: log in to the dashboard."""
    client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=True,
    )
