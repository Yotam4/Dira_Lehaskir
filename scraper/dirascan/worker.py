"""Persistent scrape worker.

Polls the ``scrape_runs`` table for queued jobs (Postgres is the queue), claims
one atomically, runs the requested crawlers, and records the result. Started in
Docker via ``dirascan worker``.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from dirascan.db.crud import filters_from_dict
from dirascan.db.models import ScrapeRun
from dirascan.db.session import SessionLocal
from dirascan.runner import run_scrape_job

logger = logging.getLogger(__name__)

# A real scrape finishes in a few minutes; anything 'running' longer than this
# is assumed to be from a crashed worker and is recovered to 'failed'.
STALE_RUNNING_MINUTES = 30


def claim_next_job(db: Session) -> ScrapeRun | None:
    """Atomically claim the oldest queued run, flipping it to 'running'.

    Uses FOR UPDATE SKIP LOCKED so multiple workers never claim the same row.
    Returns the claimed ScrapeRun, or None when the queue is empty.
    """
    row = db.execute(
        text(
            """
            UPDATE scrape_runs
            SET status = 'running'
            WHERE id = (
                SELECT id FROM scrape_runs
                WHERE status = 'queued'
                ORDER BY triggered_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
            """
        )
    ).fetchone()
    db.commit()
    if row is None:
        return None
    return db.get(ScrapeRun, row[0])


def _recover_stale_runs(db: Session) -> None:
    """Mark long-running rows (from a crashed worker) as failed."""
    result = db.execute(
        text(
            """
            UPDATE scrape_runs
            SET status = 'failed',
                completed_at = NOW(),
                error_message = 'Worker restart: recovered from stale running state'
            WHERE status = 'running'
              AND triggered_at < NOW() - make_interval(mins => :mins)
            """
        ),
        {"mins": STALE_RUNNING_MINUTES},
    )
    db.commit()
    if result.rowcount:
        logger.warning("Recovered %d stale running scrape run(s)", result.rowcount)


async def run_worker(poll_interval: float = 5.0) -> None:
    """Recover stale jobs, then loop forever processing queued jobs."""
    logger.info("Scrape worker starting (poll interval %.1fs)", poll_interval)

    recovery_db = SessionLocal()
    try:
        _recover_stale_runs(recovery_db)
    finally:
        recovery_db.close()

    while True:
        db = SessionLocal()
        try:
            run = claim_next_job(db)
            if run is None:
                await asyncio.sleep(poll_interval)
                continue
            logger.info("Claimed scrape run %s (sources=%s)", run.id, run.sources)
            filters = filters_from_dict(run.filters)
            await run_scrape_job(run.id, list(run.sources), filters, db)
        except Exception as exc:
            logger.error("Worker loop error: %s", exc, exc_info=True)
            await asyncio.sleep(poll_interval)
        finally:
            db.close()
