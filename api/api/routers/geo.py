"""
Geographic reference endpoints for the UI:
  GET /cities                — canonical Hebrew city names
  GET /neighborhoods?city=…  — distinct neighborhoods scraped for a city
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.deps import get_db
from dirascan.cities import CANONICAL_CITIES

router = APIRouter()


@router.get("/cities", response_model=list[str])
def get_cities() -> list[str]:
    """Canonical list of supported Hebrew city names."""
    return CANONICAL_CITIES


@router.get("/neighborhoods", response_model=list[str])
def get_neighborhoods(
    city: str = Query(..., description="Hebrew city name to filter by"),
    db: Session = Depends(get_db),
) -> list[str]:
    """Distinct neighborhoods seen in listings for the given city (alphabetical)."""
    rows = db.execute(
        text(
            """
            SELECT DISTINCT neighborhood
            FROM listings
            WHERE city ILIKE :city
              AND neighborhood IS NOT NULL
              AND neighborhood <> ''
            ORDER BY neighborhood
            """
        ),
        {"city": f"%{city.strip()}%"},
    ).fetchall()
    return [row[0] for row in rows]
