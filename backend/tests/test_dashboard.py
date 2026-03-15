"""
End-to-end tests for the Flask dashboard.

Covers: auth, index stats, story detail, search — all routes that previously
failed due to DetachedInstanceError and lazy loading.
"""

import json
from datetime import datetime, timezone

import pytest

from storage.ingestion import ingest
from tests.conftest import _login


def _story(guid="g1", slug="election-dates-2026", headline="Election dates announced",
           source="The Hindu"):
    return {
        "guid": guid,
        "headline": headline,
        "slug": slug,
        "primary_source": source,
        "published_at": datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        "articles": [
            {"title": "ECI announces dates", "url": "https://hindu.com/1",
             "source_name": "The Hindu", "position": 0, "is_lead": True},
            {"title": "Poll schedule out", "url": "https://ndtv.com/1",
             "source_name": "NDTV", "position": 1, "is_lead": False},
            {"title": "Opposition reacts", "url": "https://toi.com/1",
             "source_name": "Times of India", "position": 2, "is_lead": False},
        ],
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_login_page_loads(flask_client):
    resp = flask_client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_redirect_to_login_when_unauthenticated(flask_client):
    resp = flask_client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_success_redirects_to_index(flask_client):
    resp = flask_client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] in ("/", "http://localhost/")


def test_login_wrong_password(flask_client):
    resp = flask_client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Invalid credentials" in resp.data


def test_logout_clears_session(flask_client):
    _login(flask_client)
    flask_client.get("/logout")
    resp = flask_client.get("/")
    assert resp.status_code == 302


# ── Index / dashboard ─────────────────────────────────────────────────────────

def test_index_empty_db(flask_client, tmp_db):
    _login(flask_client)
    resp = flask_client.get("/")
    assert resp.status_code == 200
    assert b"LRC" in resp.data


def test_index_shows_stats(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode()
    # Story count visible
    assert "1" in html


def test_index_shows_story_headline(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/")
    assert b"Election dates announced" in resp.data


def test_index_shows_article_count(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/")
    # The article count chip should contain "3"
    assert b"3" in resp.data


def test_index_multiple_stories(flask_client, tmp_db):
    ingest([
        _story(guid="g1", slug="story-one", headline="Story One"),
        _story(guid="g2", slug="story-two", headline="Story Two"),
        _story(guid="g3", slug="story-three", headline="Story Three"),
    ])
    _login(flask_client)
    resp = flask_client.get("/")
    html = resp.data.decode()
    assert "Story One" in html
    assert "Story Two" in html
    assert "Story Three" in html


# ── Story detail ──────────────────────────────────────────────────────────────

def test_story_detail_loads(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/story/election-dates-2026")
    assert resp.status_code == 200
    assert b"Election dates announced" in resp.data


def test_story_detail_shows_sources(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/story/election-dates-2026")
    html = resp.data.decode()
    assert "The Hindu" in html
    assert "NDTV" in html
    assert "Times of India" in html


def test_story_detail_shows_article_titles(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/story/election-dates-2026")
    html = resp.data.decode()
    assert "ECI announces dates" in html
    assert "Poll schedule out" in html


def test_story_detail_404_for_unknown_slug(flask_client, tmp_db):
    _login(flask_client)
    resp = flask_client.get("/story/nonexistent-slug-xyz")
    assert resp.status_code == 404


# ── Search ────────────────────────────────────────────────────────────────────

def test_search_empty_query(flask_client, tmp_db):
    _login(flask_client)
    resp = flask_client.get("/search")
    assert resp.status_code == 200


def test_search_finds_matching_story(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/search?q=election")
    assert resp.status_code == 200
    assert b"Election dates announced" in resp.data


def test_search_shows_article_count(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/search?q=election")
    assert b"3" in resp.data


def test_search_no_results(flask_client, tmp_db):
    ingest([_story()])
    _login(flask_client)
    resp = flask_client.get("/search?q=zzz_no_match_zzz")
    assert resp.status_code == 200
    assert b"No stories matched" in resp.data


def test_search_case_insensitive(flask_client, tmp_db):
    ingest([_story(headline="Budget Announcement 2026", slug="budget-2026",
                   guid="g-budget")])
    _login(flask_client)
    resp = flask_client.get("/search?q=BUDGET")
    assert b"Budget Announcement 2026" in resp.data
