"""
CLI entry point for on-demand scraping and the background worker.

Usage:
    docker compose run --rm scraper dirascan scrape --city "תל אביב" --source yad2
    docker compose run --rm scraper dirascan scrape --city "חיפה" --source all
    docker compose run --rm scraper dirascan migrate
    dirascan worker        # persistent worker (started by docker-compose)
"""

import asyncio
import sys
from pathlib import Path

import click

from dirascan.base.crawler import SearchFilters
from dirascan.db.crud import create_scrape_run
from dirascan.db.session import SessionLocal
from dirascan.runner import CRAWLERS, run_scrape_job


@click.group()
def main():
    pass


@main.command()
@click.option("--city", default="", help="City name in Hebrew, e.g. תל אביב")
@click.option(
    "--source",
    default="all",
    type=click.Choice(["all", "yad2", "madlan", "facebook"]),
    help="Which source(s) to scrape",
)
@click.option("--price-min", default=None, type=int)
@click.option("--price-max", default=None, type=int)
@click.option("--rooms-min", default=None, type=float)
@click.option("--rooms-max", default=None, type=float)
@click.option("--max-results", default=None, type=int)
def scrape(city, source, price_min, price_max, rooms_min, rooms_max, max_results):
    """Trigger an on-demand scrape run synchronously (bypasses the queue)."""
    filters = SearchFilters(
        city=city,
        price_min=price_min,
        price_max=price_max,
        rooms_min=rooms_min,
        rooms_max=rooms_max,
        max_results=max_results,
    )

    sources = list(CRAWLERS.keys()) if source == "all" else [source]

    async def run():
        db = SessionLocal()
        try:
            scrape_run = create_scrape_run(db, sources=sources, filters=filters)
            # CLI runs immediately in-process — skip the 'queued' phase.
            scrape_run.status = "running"
            db.commit()
            await run_scrape_job(scrape_run.id, sources, filters, db)
            db.refresh(scrape_run)
            click.echo(
                f"\nDone. Found {scrape_run.listings_found or 0}, "
                f"new {scrape_run.listings_new or 0}. Status: {scrape_run.status}."
            )
            if scrape_run.status == "failed":
                click.echo(f"Errors: {scrape_run.error_message}", err=True)
                sys.exit(1)
        finally:
            db.close()

    asyncio.run(run())


@main.command()
@click.option("--poll-interval", default=5.0, type=float, help="Seconds between polls when idle")
def worker(poll_interval):
    """Persistent worker: polls scrape_runs for queued jobs and executes them."""
    from dirascan.worker import run_worker

    asyncio.run(run_worker(poll_interval=poll_interval))


@main.command()
def migrate():
    """Run Alembic migrations (alias for alembic upgrade head)."""
    import subprocess

    # In Docker, alembic.ini is at /app; in local dev it's in the scraper/ directory
    alembic_dir = "/app" if Path("/app/alembic.ini").exists() else str(Path(__file__).parent.parent)
    result = subprocess.run(["alembic", "upgrade", "head"], cwd=alembic_dir)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
