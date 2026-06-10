"""
Tests for POST /scrape/trigger and GET /scrape/runs/{id}.

All DB calls and background tasks are mocked.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from .conftest import _make_mock_scrape_run


# ---------------------------------------------------------------------------
# POST /scrape/trigger
# ---------------------------------------------------------------------------

def test_trigger_scrape_returns_run_id(client, mock_db):
    run = _make_mock_scrape_run()

    # upsert_listing and CRUD helpers are called inside the router
    with patch("api.routers.scrape.create_scrape_run", return_value=run) as mock_create:
        mock_db.commit = MagicMock()
        resp = client.post(
            "/scrape/trigger",
            json={"sources": ["yad2"], "filters": {"city": "תל אביב"}},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "queued"
    assert "triggered_at" in data


def test_trigger_scrape_default_sources(client, mock_db):
    run = _make_mock_scrape_run()
    with patch("api.routers.scrape.create_scrape_run", return_value=run):
        resp = client.post("/scrape/trigger", json={"filters": {}})
    assert resp.status_code == 202


def test_trigger_scrape_bad_payload(client):
    # sources must be a list
    resp = client.post("/scrape/trigger", json={"sources": "yad2"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /scrape/runs/{run_id}
# ---------------------------------------------------------------------------

def test_get_run_running(client, mock_db):
    run = _make_mock_scrape_run(status="running")
    mock_db.get.return_value = run

    resp = client.get(f"/scrape/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["completed_at"] is None
    assert data["listings_found"] is None


def test_get_run_completed(client, mock_db):
    run = _make_mock_scrape_run(
        status="completed",
        completed_at=datetime.utcnow(),
        listings_found=42,
        listings_new=7,
    )
    mock_db.get.return_value = run

    resp = client.get(f"/scrape/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["listings_found"] == 42
    assert data["listings_new"] == 7


def test_get_run_failed(client, mock_db):
    run = _make_mock_scrape_run(
        status="failed",
        completed_at=datetime.utcnow(),
        error_message="Playwright timeout",
    )
    mock_db.get.return_value = run

    resp = client.get(f"/scrape/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "Playwright timeout"


def test_get_run_not_found(client, mock_db):
    mock_db.get.return_value = None
    resp = client.get(f"/scrape/runs/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Scrape run not found"


def test_get_run_invalid_uuid(client):
    resp = client.get("/scrape/runs/not-a-uuid")
    assert resp.status_code == 422
