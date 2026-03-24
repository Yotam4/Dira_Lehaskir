"""
POST /scrape/trigger — on-demand scrape endpoint.

Creates a scrape_run record immediately and fires the crawlers as a
FastAPI BackgroundTask so the HTTP response returns right away.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.scrape import ScrapeRequest, ScrapeRunDetailResponse, ScrapeRunResponse
from dirascan.base.crawler import SearchFilters
from dirascan.db.models import ScrapeRun
from dirascan.crawlers.yad2 import Yad2Crawler
from dirascan.crawlers.madlan import MadlanCrawler
from dirascan.crawlers.facebook import FacebookCrawler
from dirascan.db.crud import create_scrape_run, complete_scrape_run, upsert_listing
from dirascan.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()

CRAWLERS = {
    "yad2": Yad2Crawler,
    "madlan": MadlanCrawler,
    "facebook": FacebookCrawler,
}


def _to_search_filters(filters) -> SearchFilters:
    return SearchFilters(
        city=filters.city,
        neighborhoods=filters.neighborhoods,
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


async def _run_scrape(run_id, sources: list[str], filters: SearchFilters) -> None:
    """Background task: runs crawlers and writes results to DB."""
    db = SessionLocal()
    total_found = 0
    total_new = 0
    error_msg = None

    try:
        run = db.query(__import__("dirascan.db.models", fromlist=["ScrapeRun"]).ScrapeRun).get(run_id)

        for source in sources:
            crawler_cls = CRAWLERS[source]
            try:
                async with crawler_cls() as crawler:
                    listings = await crawler.scrape(filters)
                for raw in listings:
                    raw.crawl_run_id = run_id
                    _, is_new = upsert_listing(db, raw)
                    total_found += 1
                    if is_new:
                        total_new += 1
                db.commit()
                logger.info("Scrape %s: %s found %d listings", run_id, source, len(listings))
            except NotImplementedError:
                logger.warning("Crawler %s not yet implemented — skipping", source)
            except Exception as exc:
                logger.error("Crawler %s error: %s", source, exc, exc_info=True)
                error_msg = str(exc)

        complete_scrape_run(
            db,
            run,
            listings_found=total_found,
            listings_new=total_new,
            error_message=error_msg,
        )
        db.commit()
    except Exception as exc:
        logger.error("Scrape run %s fatal error: %s", run_id, exc, exc_info=True)
        db.rollback()
    finally:
        db.close()


@router.post("/trigger", response_model=ScrapeRunResponse)
def trigger_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    filters = _to_search_filters(request.filters)
    run = create_scrape_run(db, sources=request.sources, filters=filters)
    db.commit()

    background_tasks.add_task(_run_scrape, run.id, request.sources, filters)

    return ScrapeRunResponse(
        run_id=run.id,
        status=run.status,
        triggered_at=run.triggered_at,
    )


@router.get("/runs/{run_id}", response_model=ScrapeRunDetailResponse)
def get_scrape_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    """Poll the status of a triggered scrape run."""
    run = db.query(ScrapeRun).get(run_id)
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
