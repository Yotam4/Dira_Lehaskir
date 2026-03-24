"""
Tests for GET /listings and GET /listings/{id}.

All DB calls are mocked — no real database required.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from .conftest import _make_mock_listing


# ---------------------------------------------------------------------------
# GET /health — sanity check
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /listings — basic structure
# ---------------------------------------------------------------------------

def test_get_listings_empty(client, mock_db):
    # DB returns no listings
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    resp = client.get("/listings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_get_listings_returns_items(client, mock_db):
    listing = _make_mock_listing()
    q = mock_db.query.return_value
    q.count.return_value = 1
    q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [listing]

    resp = client.get("/listings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["source"] == "yad2"
    assert item["city"] == "תל אביב"
    assert item["price"] == 5500


def test_get_listings_pagination(client, mock_db):
    q = mock_db.query.return_value
    q.count.return_value = 50
    q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    resp = client.get("/listings?page=2&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["page_size"] == 10


def test_get_listings_invalid_page(client):
    resp = client.get("/listings?page=0")
    assert resp.status_code == 422  # FastAPI validation error


def test_get_listings_page_size_cap(client):
    resp = client.get("/listings?page_size=999")
    assert resp.status_code == 422  # page_size max is 100


# ---------------------------------------------------------------------------
# GET /listings/{id}
# ---------------------------------------------------------------------------

def test_get_listing_found(client, mock_db):
    listing = _make_mock_listing()
    mock_db.get.return_value = listing

    resp = client.get(f"/listings/{listing.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "yad2"
    assert data["title"] == "דירת 3 חדרים בתל אביב"


def test_get_listing_not_found(client, mock_db):
    mock_db.get.return_value = None
    resp = client.get(f"/listings/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Listing not found"


def test_get_listing_invalid_uuid(client):
    resp = client.get("/listings/not-a-uuid")
    assert resp.status_code == 422
