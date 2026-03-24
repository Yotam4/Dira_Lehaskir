"""
GET /listings         — paginated listing search with spatial + attribute filters
GET /listings/{id}    — single listing detail
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID, ST_Within
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.listing import ListingResponse, ListingsPage
from dirascan.db.models import Listing

router = APIRouter()


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
    source: Optional[str] = Query(None, description="yad2 | madlan | facebook"),
    price_min: Optional[int] = Query(None),
    price_max: Optional[int] = Query(None),
    rooms_min: Optional[float] = Query(None),
    rooms_max: Optional[float] = Query(None),
    # --- Pagination ---
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Listing)

    # Spatial: polygon takes precedence over point+radius
    if polygon_geojson:
        try:
            geom = func.ST_GeomFromGeoJSON(polygon_geojson)
            q = q.filter(ST_Within(Listing.location, geom))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid polygon_geojson")
    elif lat is not None and lng is not None and radius_m is not None:
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        q = q.filter(
            ST_DWithin(
                func.cast(Listing.location, func.Geography),
                func.cast(point, func.Geography),
                radius_m,
            )
        )

    if city:
        q = q.filter(Listing.city.ilike(f"%{city}%"))
    if neighborhood:
        q = q.filter(Listing.neighborhood.ilike(f"%{neighborhood}%"))
    if source:
        q = q.filter(Listing.source == source)
    if price_min is not None:
        q = q.filter(Listing.price >= price_min)
    if price_max is not None:
        q = q.filter(Listing.price <= price_max)
    if rooms_min is not None:
        q = q.filter(Listing.rooms >= rooms_min)
    if rooms_max is not None:
        q = q.filter(Listing.rooms <= rooms_max)

    total = q.count()
    items = q.order_by(Listing.scraped_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return ListingsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: uuid.UUID, db: Session = Depends(get_db)):
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
