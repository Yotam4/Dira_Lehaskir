"""Shared pytest config for the scraper test suite.

Adds the opt-in gate for live e2e tests (which hit real websites) and provides
crawler-instance / SearchFilters fixtures used across the offline tests.
"""

from __future__ import annotations

import os

import pytest

from dirascan.base.crawler import SearchFilters
from dirascan.crawlers.facebook import FacebookCrawler
from dirascan.crawlers.madlan import MadlanCrawler
from dirascan.crawlers.yad2 import Yad2Crawler


# ---------------------------------------------------------------------------
# Live-test opt-in gate
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live e2e crawler tests that hit real websites (slow, requires network).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: hits real Yad2/Madlan/Facebook over the network (opt-in, skipped by default)",
    )


def _live_enabled(config) -> bool:
    return bool(config.getoption("--run-live")) or os.getenv("RUN_LIVE_CRAWLER_TESTS") == "1"


def pytest_collection_modifyitems(config, items):
    if _live_enabled(config):
        return
    skip_live = pytest.mark.skip(
        reason="live test — pass --run-live or set RUN_LIVE_CRAWLER_TESTS=1 to run",
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def filters_tel_aviv() -> SearchFilters:
    return SearchFilters(city="תל אביב", max_results=10)


@pytest.fixture
def filters_empty() -> SearchFilters:
    return SearchFilters()


@pytest.fixture
def yad2_crawler() -> Yad2Crawler:
    return Yad2Crawler()


@pytest.fixture
def madlan_crawler() -> MadlanCrawler:
    return MadlanCrawler()


@pytest.fixture
def facebook_crawler() -> FacebookCrawler:
    return FacebookCrawler()
