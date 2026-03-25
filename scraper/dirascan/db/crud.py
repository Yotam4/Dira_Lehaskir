"""
CRUD helpers used by both the API trigger endpoint and the CLI.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from dirascan.base.crawler import RawListing, SearchFilters
from dirascan.db.models import Listing, ListingSource, ScrapeRun


# ---------------------------------------------------------------------------
# Scrape runs
# ---------------------------------------------------------------------------

def create_scrape_run(
    db: Session,
    sources: list[str],
    filters: SearchFilters,
) -> ScrapeRun:
    run = ScrapeRun(
        id=uuid.uuid4(),
        sources=sources,
        filters=_filters_to_dict(filters),
        status="running",
    )
    db.add(run)
    db.flush()
    return run


def complete_scrape_run(
    db: Session,
    run: ScrapeRun,
    *,
    listings_found: int,
    listings_new: int,
    error_message: str | None = None,
) -> None:
    run.completed_at = datetime.now(timezone.utc)
    run.status = "failed" if error_message else "completed"
    run.listings_found = listings_found
    run.listings_new = listings_new
    run.error_message = error_message
    db.flush()


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------

def upsert_listing(db: Session, raw: RawListing) -> tuple[Listing, bool]:
    """
    Insert or update a listing from a RawListing.

    Returns (listing, is_new) where is_new=True when a new row was created.

    Deduplication strategy:
    1. Try to find an existing ListingSource row with the same (source, source_id).
    2. If found → update the canonical Listing and update last_seen_at.
    3. If not found → insert a new Listing + ListingSource.
    """
    existing_source = (
        db.query(ListingSource)
        .filter_by(source=raw.source, source_id=raw.source_id)
        .first()
    )

    location = None
    if raw.lat is not None and raw.lng is not None:
        location = WKTElement(f"POINT({raw.lng} {raw.lat})", srid=4326)

    now = datetime.now(timezone.utc)

    if existing_source:
        listing = db.get(Listing, existing_source.listing_id)
        if listing is None:
            # Orphaned source row (listing was deleted) — clean up and re-insert
            db.delete(existing_source)
            db.flush()
        else:
            listing.title = raw.title or listing.title
            listing.description = raw.description or listing.description
            listing.price = raw.price if raw.price is not None else listing.price
            listing.rooms = raw.rooms if raw.rooms is not None else listing.rooms
            listing.sqm = raw.sqm if raw.sqm is not None else listing.sqm
            listing.floor = raw.floor if raw.floor is not None else listing.floor
            listing.location = location or listing.location
            listing.amenities = raw.amenities or listing.amenities
            listing.images = raw.images or listing.images
            listing.raw_data = raw.raw_data or listing.raw_data
            listing.updated_at = now
            listing.scraped_at = raw.scraped_at
            existing_source.last_seen_at = now
            db.flush()
            return listing, False

    listing = Listing(
        id=uuid.uuid4(),
        source=raw.source,
        original_url=raw.original_url,
        title=raw.title or "",
        description=raw.description,
        price=raw.price,
        rooms=raw.rooms,
        sqm=raw.sqm,
        floor=raw.floor,
        address=raw.address,
        city=raw.city or "",
        neighborhood=raw.neighborhood,
        location=location,
        amenities=raw.amenities,
        images=raw.images,
        raw_data=raw.raw_data,
        scraped_at=raw.scraped_at,
    )
    db.add(listing)
    db.flush()

    # ON CONFLICT DO UPDATE prevents IntegrityError if two scrape tasks race to
    # insert the same (source, source_id) concurrently.
    stmt = (
        pg_insert(ListingSource)
        .values(
            listing_id=listing.id,
            source=raw.source,
            source_id=raw.source_id,
            original_url=raw.original_url,
        )
        .on_conflict_do_update(
            constraint="uq_listing_sources_source_id",
            set_={"last_seen_at": func.now()},
        )
    )
    db.execute(stmt)
    db.flush()

    return listing, True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filters_to_dict(filters: SearchFilters) -> dict[str, Any]:
    return {
        "city": filters.city,
        "neighborhoods": filters.neighborhoods,
        "lat": filters.lat,
        "lng": filters.lng,
        "radius_m": filters.radius_m,
        "polygon_geojson": filters.polygon_geojson,
        "price_min": filters.price_min,
        "price_max": filters.price_max,
        "rooms_min": filters.rooms_min,
        "rooms_max": filters.rooms_max,
        "max_results": filters.max_results,
    }
