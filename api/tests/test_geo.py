"""Tests for the geo reference endpoints: GET /cities and GET /neighborhoods."""

from __future__ import annotations

from dirascan.cities import CANONICAL_CITIES


def test_cities_returns_canonical_list(client):
    resp = client.get("/cities")
    assert resp.status_code == 200
    body = resp.json()
    assert body == CANONICAL_CITIES
    assert "תל אביב" in body


def test_neighborhoods_requires_city(client):
    # city is a required query param → 422 when missing
    resp = client.get("/neighborhoods")
    assert resp.status_code == 422


def test_neighborhoods_returns_rows(client, mock_db):
    mock_db.execute.return_value.fetchall.return_value = [("לב העיר",), ("נווה צדק",)]
    resp = client.get("/neighborhoods", params={"city": "תל אביב"})
    assert resp.status_code == 200
    assert resp.json() == ["לב העיר", "נווה צדק"]
    # city is passed as a bound parameter (no string interpolation into SQL),
    # resilient to positional-vs-keyword param passing.
    assert _execute_params(mock_db)["city"] == "%תל אביב%"


def test_neighborhoods_empty_when_no_listings(client, mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    resp = client.get("/neighborhoods", params={"city": "חיפה"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_neighborhoods_strips_whitespace(client, mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    client.get("/neighborhoods", params={"city": "  תל אביב  "})
    assert _execute_params(mock_db)["city"] == "%תל אביב%"


def _execute_params(mock_db) -> dict:
    """Bound params for the last db.execute call (positional or keyword)."""
    call = mock_db.execute.call_args
    return call.kwargs.get("parameters") or (call.args[1] if len(call.args) > 1 else {})
