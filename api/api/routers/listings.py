"""
GET /listings         — paginated listing search with spatial + attribute filters
GET /listings/{id}    — single listing detail
"""

from __future__ import annotations

import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID, ST_Within
from geoalchemy2.types import Geography
from sqlalchemy import cast, func, text
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.listing import ListingResponse, ListingsPage
from dirascan.db.models import Listing

router = APIRouter()

_SORT_COLUMNS = {
    "price": Listing.price,
    "rooms": Listing.rooms,
    "sqm": Listing.sqm,
    "scraped_at": Listing.scraped_at,
}


@router.get("", response_model=ListingsPage)
def get_listings(
    # --- Spatial filters (mutually exclusive, polygon takes precedence) ---
    lat: Optional[float] = Query(None, description="Latitude for point+radius search"),
    lng: Optional[float] = Query(None, description="Longitude for point+radius search"),
    radius_m: Optional[int] = Query(None, description="Radius in metres for point+radius search"),
    polygon_geojson: Optional[str] = Query(
        None,
        description="GeoJSON Polygon geometry string for drawn-polygon search",
    ),
    # --- City / neighbourhood text filters ---
    city: Optional[str] = Query(None),
    neighborhood: Optional[str] = Query(None),
    # --- Attribute filters ---
    source: Optional[str] = Query(None, description="yad2 | madlan | facebook (single, legacy)"),
    sources: Optional[List[str]] = Query(None, description="Repeatable: sources=yad2&sources=madlan"),
    price_min: Optional[int] = Query(None),
    price_max: Optional[int] = Query(None),
    rooms_min: Optional[float] = Query(None),
    rooms_max: Optional[float] = Query(None),
    # --- Sort ---
    sort_by: Optional[str] = Query(None, description="price | rooms | sqm | scraped_at"),
    order: Optional[str] = Query(None, description="asc | desc"),
    # --- Pagination ---
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Listing)

    # Spatial: polygon takes precedence over point+radius
    if polygon_geojson:
        try:
            poly = json.loads(polygon_geojson)
            if not isinstance(poly, dict) or poly.get("type") != "Polygon":
                raise ValueError("GeoJSON type must be 'Polygon'")
            if not poly.get("coordinates"):
                raise ValueError("Polygon must have coordinates")
            geom = func.ST_GeomFromGeoJSON(polygon_geojson)
            q = q.filter(ST_Within(Listing.location, geom))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid polygon_geojson: {exc}")
    elif lat is not None and lng is not None and radius_m is not None and radius_m > 0:
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        q = q.filter(
            ST_DWithin(
                cast(Listing.location, Geography),
                cast(point, Geography),
                radius_m,
            )
        )

    if city:
        q = q.filter(Listing.city.ilike(f"%{city.strip()}%"))
    if neighborhood:
        q = q.filter(Listing.neighborhood.ilike(f"%{neighborhood.strip()}%"))

    # Multi-source filter: `sources` (array) takes precedence over `source` (single, legacy)
    active_sources = sources if sources else ([source] if source else None)
    if active_sources:
        q = q.filter(Listing.source.in_(active_sources))

    if price_min is not None:
        q = q.filter(Listing.price >= price_min)
    if price_max is not None:
        q = q.filter(Listing.price <= price_max)
    if rooms_min is not None:
        q = q.filter(Listing.rooms >= rooms_min)
    if rooms_max is not None:
        q = q.filter(Listing.rooms <= rooms_max)

    total = q.count()

    # Sort
    sort_col = _SORT_COLUMNS.get(sort_by or "", Listing.scraped_at)
    if order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return ListingsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: uuid.UUID, db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
