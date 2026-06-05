"""Shared crawl-and-persist logic.

Used by both the background worker (``dirascan worker``) and the synchronous CLI
(``dirascan scrape``). The API no longer imports any of this — it only enqueues
ScrapeRun rows.
"""

from __future__ import annotations

import logging
import uuid

from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session

from dirascan.base.crawler import BaseCrawler, SearchFilters
from dirascan.crawlers.madlan import MadlanCrawler
from dirascan.crawlers.yad2 import Yad2Crawler
from dirascan.db.crud import complete_scrape_run, upsert_listing
from dirascan.db.models import ScrapeRun

logger = logging.getLogger(__name__)


# Crawler registry. Facebook is optional (its scraper lib has a fragile build),
# so it is only registered when the `facebook` extra is installed.
CRAWLERS: dict[str, type[BaseCrawler]] = {
    "yad2": Yad2Crawler,
    "madlan": MadlanCrawler,
}

try:  # pragma: no cover - depends on optional extra being installed
    from dirascan.crawlers.facebook import FacebookCrawler

    CRAWLERS["facebook"] = FacebookCrawler
except ImportError:
    logger.info("facebook-scraper not installed — Facebook source disabled")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _scrape_with_retry(crawler_cls: type[BaseCrawler], filters: SearchFilters):
    async with crawler_cls() as crawler:
        return await crawler.scrape(filters)


async def run_scrape_job(
    run_id: uuid.UUID,
    sources: list[str],
    filters: SearchFilters,
    db: Session,
) -> None:
    """Run the requested sources for an existing ScrapeRun and persist results.

    The caller owns the session and must have already created the run (and, for
    the worker, claimed it by setting status='running'). On any fatal error the
    run is marked failed so the UI never hangs.
    """
    total_found = 0
    total_new = 0
    errors: list[str] = []

    logger.info(
        "Scrape run %s starting: sources=%s city=%r price=%s-%s rooms=%s-%s",
        run_id,
        sources,
        filters.city,
        filters.price_min,
        filters.price_max,
        filters.rooms_min,
        filters.rooms_max,
    )

    try:
        run = db.get(ScrapeRun, run_id)
        if not run:
            logger.error("Scrape run %s not found in database — cannot proceed", run_id)
            return

        for source in sources:
            crawler_cls = CRAWLERS.get(source)
            if crawler_cls is None:
                logger.warning("Source %r not available (extra not installed?) — skipping", source)
                errors.append(f"{source}: crawler not available")
                continue
            try:
                listings = await _scrape_with_retry(crawler_cls, filters)
                for raw in listings:
                    raw.crawl_run_id = run_id
                    _, is_new = upsert_listing(db, raw)
                    total_found += 1
                    if is_new:
                        total_new += 1
                db.commit()
                logger.info("Scrape %s: %s found %d listings", run_id, source, len(listings))
            except Exception as exc:
                logger.error("Crawler %s error: %s", source, exc, exc_info=True)
                errors.append(f"{source}: {exc}")

        complete_scrape_run(
            db,
            run,
            listings_found=total_found,
            listings_new=total_new,
            error_message="; ".join(errors) if errors else None,
        )
        db.commit()
    except Exception as exc:
        logger.error("Scrape run %s fatal error: %s", run_id, exc, exc_info=True)
        db.rollback()
        # Best-effort: mark the run as failed so the UI doesn't hang forever.
        try:
            run = db.get(ScrapeRun, run_id)
            if run and run.status in ("queued", "running"):
                complete_scrape_run(
                    db,
                    run,
                    listings_found=total_found,
                    listings_new=total_new,
                    error_message=str(exc),
                )
                db.commit()
        except Exception:
            logger.error("Scrape run %s: could not mark as failed", run_id)
