"""Live end-to-end crawler tests — they hit the real Yad2/Madlan/Facebook sites.

These are the "is real data actually flowing in?" checks: they run a real scrape
and assert the results are non-empty and well-formed (key fields populated, types
correct, coordinates inside Israel, ids unique). They catch upstream breakage that
offline fixture tests cannot — at the cost of being slow and network-dependent.

OPT-IN ONLY. Skipped unless you pass ``--run-live`` or set
``RUN_LIVE_CRAWLER_TESTS=1`` (see conftest.py). Requires a Playwright browser:

    playwright install chromium
    RUN_LIVE_CRAWLER_TESTS=1 pytest tests/test_crawlers_live.py -v
"""

from __future__ import annotations

import asyncio

import pytest

from dirascan.base.crawler import RawListing, SearchFilters
from dirascan.crawlers.facebook import FacebookCrawler
from dirascan.crawlers.madlan import MadlanCrawler
from dirascan.crawlers.yad2 import Yad2Crawler
from dirascan.settings import settings

# Israel bounding box — coordinates outside this are almost certainly wrong.
_IL_LNG = (34.0, 36.0)
_IL_LAT = (29.0, 34.0)

_SCRAPE_TIMEOUT_S = 180


def _fraction_populated(listings: list[RawListing], attr: str) -> float:
    if not listings:
        return 0.0
    return sum(1 for l in listings if getattr(l, attr) is not None) / len(listings)


def _assert_well_formed(listings: list[RawListing], source: str) -> None:
    assert len(listings) > 0, f"{source}: scrape returned zero listings — data not flowing"

    # Identity / dedupe integrity.
    assert all(l.source == source for l in listings)
    assert all(l.source_id for l in listings), f"{source}: blank source_id present"
    ids = [l.source_id for l in listings]
    assert len(set(ids)) == len(ids), f"{source}: duplicate source_ids — dedupe collapsed rows"
    assert all(l.original_url for l in listings), f"{source}: missing original_url"

    # Completeness thresholds — catch a parser that silently stops extracting fields.
    assert _fraction_populated(listings, "price") >= 0.6, f"{source}: too few prices parsed"
    assert _fraction_populated(listings, "rooms") >= 0.5, f"{source}: too few room counts parsed"

    # Type / range correctness on the populated values.
    for l in listings:
        if l.price is not None:
            assert isinstance(l.price, int) and l.price > 0
        if l.rooms is not None:
            assert isinstance(l.rooms, float) and l.rooms > 0
        if l.lat is not None and l.lng is not None:
            assert _IL_LNG[0] <= l.lng <= _IL_LNG[1], f"{source}: lng {l.lng} outside Israel"
            assert _IL_LAT[0] <= l.lat <= _IL_LAT[1], f"{source}: lat {l.lat} outside Israel"


@pytest.mark.live
class TestYad2Live:
    async def test_scrape_returns_well_formed_data(self):
        crawler = Yad2Crawler()
        filters = SearchFilters(city="תל אביב", max_results=10)
        results = await asyncio.wait_for(crawler.scrape(filters), timeout=_SCRAPE_TIMEOUT_S)
        assert len(results) <= 10  # max_results respected
        _assert_well_formed(results, "yad2")
        assert any(l.lat is not None and l.lng is not None for l in results), (
            "yad2: no coordinates on any listing"
        )


@pytest.mark.live
class TestMadlanLive:
    async def test_scrape_returns_well_formed_data(self):
        crawler = MadlanCrawler()
        filters = SearchFilters(city="תל אביב", max_results=10)
        results = await asyncio.wait_for(crawler.scrape(filters), timeout=_SCRAPE_TIMEOUT_S)
        assert len(results) <= 10
        _assert_well_formed(results, "madlan")


@pytest.mark.live
class TestFacebookLive:
    async def test_scrape_runs_and_parses(self):
        if not (settings.facebook_email and settings.facebook_password):
            pytest.skip("Facebook live test needs FACEBOOK_EMAIL / FACEBOOK_PASSWORD")

        crawler = FacebookCrawler()
        filters = SearchFilters(city="תל אביב", max_results=5)
        # Public/group scraping is inherently variable — assert it runs without
        # error and that whatever comes back is a valid RawListing.
        results = await asyncio.wait_for(crawler.scrape(filters), timeout=_SCRAPE_TIMEOUT_S)
        assert isinstance(results, list)
        assert len(results) <= 5
        for l in results:
            assert l.source == "facebook"
            assert l.source_id
            assert l.description
