"""
CLI entry point for on-demand scraping.

Usage:
    docker compose run --rm scraper dirascan scrape --city "תל אביב" --source yad2
    docker compose run --rm scraper dirascan scrape --city "חיפה" --source all
    docker compose run --rm scraper dirascan migrate
"""

import asyncio
import sys
from pathlib import Path

import click

from dirascan.base.crawler import SearchFilters
from dirascan.crawlers.yad2 import Yad2Crawler
from dirascan.crawlers.madlan import MadlanCrawler
from dirascan.crawlers.facebook import FacebookCrawler
from dirascan.db.session import SessionLocal
from dirascan.db.crud import create_scrape_run, complete_scrape_run, upsert_listing

CRAWLERS = {
    "yad2": Yad2Crawler,
    "madlan": MadlanCrawler,
    "facebook": FacebookCrawler,
}


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
    """Trigger an on-demand scrape run."""
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
            db.commit()

            total_found = 0
            total_new = 0
            error_occurred = False

            for src in sources:
                crawler_cls = CRAWLERS[src]
                click.echo(f"Scraping {src}...")
                try:
                    async with crawler_cls() as crawler:
                        listings = await crawler.scrape(filters)
                    for raw in listings:
                        raw.crawl_run_id = scrape_run.id
                        _, is_new = upsert_listing(db, raw)
                        total_found += 1
                        if is_new:
                            total_new += 1
                    db.commit()
                    click.echo(f"  {src}: {len(listings)} listings")
                except NotImplementedError:
                    click.echo(f"  {src}: not yet implemented — skipping")
                except Exception as exc:
                    click.echo(f"  {src}: ERROR — {exc}", err=True)
                    error_occurred = True

            complete_scrape_run(
                db,
                scrape_run,
                listings_found=total_found,
                listings_new=total_new,
            )
            db.commit()
            click.echo(f"\nDone. Found {total_found}, new {total_new}.")
            if error_occurred:
                sys.exit(1)
        finally:
            db.close()

    asyncio.run(run())


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
