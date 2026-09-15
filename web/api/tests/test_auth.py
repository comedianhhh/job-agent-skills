"""TRACKER_TOKEN gates every /api route except health (and the OpenAPI docs)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from tracker_api.auth import token_matches
from tracker_api.main import create_app


@pytest.fixture
def locked(settings):
    return TestClient(create_app(replace(settings, token="s3cret")))


def test_open_when_token_unset(client):
    assert client.get("/api/auth").status_code == 200
    assert client.get("/api/health").json()["auth"] is False


def test_locked_rejects_missing_and_wrong_token(locked):
    r = locked.get("/api/tracker")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert locked.get("/api/auth", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert locked.get("/api/auth", headers={"Authorization": "Basic s3cret"}).status_code == 401
    assert locked.patch("/api/tracker/x", json={"status": "APPLIED"}).status_code == 401
    assert locked.post("/api/scans", json={}).status_code == 401


def test_locked_accepts_token(locked):
    h = {"Authorization": "Bearer s3cret"}
    assert locked.get("/api/auth", headers=h).status_code == 200
    assert len(locked.get("/api/tracker", headers=h).json()["rows"]) == 5
    assert locked.get("/api/health").json()["auth"] is True  # health stays public
    assert locked.get("/openapi.json").status_code == 200


def test_preflight_passes_without_token(locked):
    r = locked.options(
        "/api/tracker",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "PATCH"},
    )
    assert r.status_code == 200


def test_token_matches():
    assert token_matches("Bearer abc", "abc")
    assert token_matches("bearer abc ", "abc")
    assert not token_matches("Bearer abd", "abc")
    assert not token_matches("Bearer ", "abc")
    assert not token_matches(None, "abc")
    assert not token_matches("abc", "abc")
