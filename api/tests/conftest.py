"""
Shared pytest fixtures for the API test suite.

The API depends on the `dirascan` package which is volume-mounted at /scraper
in Docker. For local test runs, we add the scraper package path to sys.path
before any imports happen.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# Make the dirascan package importable from the repo layout
_SCRAPER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scraper"))
if _SCRAPER_DIR not in sys.path:
    sys.path.insert(0, _SCRAPER_DIR)

# Also patch the /scraper path that main.py inserts so it doesn't fail
if "/scraper" not in sys.path:
    sys.path.insert(0, _SCRAPER_DIR)

from fastapi.testclient import TestClient

from api.deps import get_db


def _make_mock_listing(**kwargs):
    """Return a MagicMock that looks like a Listing ORM object."""
    defaults = dict(
        id=uuid.uuid4(),
        source="yad2",
        original_url="https://yad2.co.il/item/abc123",
        title="דירת 3 חדרים בתל אביב",
        description="דירה מרווחת",
        price=5500,
        rooms=3.0,
        sqm=75.0,
        floor=2,
        address="רחוב דיזנגוף 1",
        city="תל אביב",
        neighborhood="לב העיר",
        lat=32.08,
        lng=34.78,
        amenities={},
        images=[],
        scraped_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_mock_scrape_run(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        status="running",
        triggered_at=datetime.utcnow(),
        completed_at=None,
        listings_found=None,
        listings_new=None,
        error_message=None,
    )
    defaults.update(kwargs)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.fixture
def mock_listing():
    return _make_mock_listing()


@pytest.fixture
def mock_scrape_run():
    return _make_mock_scrape_run()


@pytest.fixture
def mock_db():
    """A MagicMock that mimics a SQLAlchemy Session with a chainable query API."""
    db = MagicMock()
    q = MagicMock()
    # filter() returns the same mock so multiple .filter() calls chain cleanly
    q.filter.return_value = q
    q.count.return_value = 0
    q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    q.get.return_value = None
    db.query.return_value = q
    return db


@pytest.fixture
def client(mock_db):
    """TestClient with the DB dependency overridden."""
    # Import here so sys.path is already patched
    import main  # noqa: F401 — registers routes
    from main import app

    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
