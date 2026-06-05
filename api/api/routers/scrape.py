"""
POST /scrape/trigger — enqueue an on-demand scrape.

The API does NOT run crawlers. It creates a scrape_runs row with status
'queued' and returns immediately; a separate worker process (the scraper
service running `dirascan worker`) claims and executes the job. This keeps
Playwright/Chromium out of the API container entirely.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.scrape import ScrapeRequest, ScrapeRunDetailResponse, ScrapeRunResponse
from dirascan.base.crawler import SearchFilters
from dirascan.db.crud import create_scrape_run
from dirascan.db.models import ScrapeRun

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_SOURCES = {"yad2", "madlan", "facebook"}


def _to_search_filters(filters) -> SearchFilters:
    return SearchFilters(
        city=filters.city,
        neighborhoods=[filters.neighborhood] if filters.neighborhood else [],
        lat=filters.lat,
        lng=filters.lng,
        radius_m=filters.radius_m,
        polygon_geojson=filters.polygon_geojson,
        price_min=filters.price_min,
        price_max=filters.price_max,
        rooms_min=filters.rooms_min,
        rooms_max=filters.rooms_max,
        max_results=filters.max_results,
    )


@router.post("/trigger", response_model=ScrapeRunResponse, status_code=202)
def trigger_scrape(request: ScrapeRequest, db: Session = Depends(get_db)):
    invalid = sorted(set(request.sources) - VALID_SOURCES)
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unknown sources: {invalid}")

    filters = _to_search_filters(request.filters)
    run = create_scrape_run(db, sources=request.sources, filters=filters)
    db.commit()

    logger.info("Enqueued scrape run %s: sources=%s city=%r", run.id, request.sources, filters.city)

    return ScrapeRunResponse(
        run_id=run.id,
        status=run.status,
        triggered_at=run.triggered_at,
    )


@router.get("/runs/{run_id}", response_model=ScrapeRunDetailResponse)
def get_scrape_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    """Poll the status of a triggered scrape run."""
    run = db.get(ScrapeRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scrape run not found")
    return ScrapeRunDetailResponse(
        run_id=run.id,
        status=run.status,
        triggered_at=run.triggered_at,
        completed_at=run.completed_at,
        listings_found=run.listings_found,
        listings_new=run.listings_new,
        error_message=run.error_message,
    )
