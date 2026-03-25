from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Search filters — passed to every crawler to constrain the search.
# Supports three modes (can be combined):
#   1. City / neighborhood text search
#   2. Point + radius (lat/lng + radius_m)
#   3. Drawn polygon (GeoJSON geometry string)
# ---------------------------------------------------------------------------

@dataclass
class SearchFilters:
    city: str = ""
    neighborhoods: list[str] = field(default_factory=list)

    # Point + radius search
    lat: float | None = None
    lng: float | None = None
    radius_m: int | None = None        # metres, e.g. 1000 for 1 km

    # Drawn polygon search (GeoJSON Polygon geometry as a JSON string)
    # e.g. '{"type":"Polygon","coordinates":[[[34.77,32.07],[34.78,32.07],...]]}'
    polygon_geojson: str | None = None

    price_min: int | None = None
    price_max: int | None = None
    rooms_min: float | None = None     # float: 1.5, 2, 2.5, 3, 3.5 …
    rooms_max: float | None = None
    max_results: int | None = None     # safety cap per run


# ---------------------------------------------------------------------------
# Raw listing — unvalidated data straight from a source.
# ---------------------------------------------------------------------------

@dataclass
class RawListing:
    source: str                          # 'yad2' | 'madlan' | 'facebook'
    source_id: str                       # platform's own ID for this listing
    original_url: str | None = None
    title: str | None = None
    description: str | None = None
    price_raw: str | None = None         # raw string, e.g. "₪4,500"
    price: int | None = None             # parsed ILS integer
    rooms_raw: str | None = None
    rooms: float | None = None
    sqm_raw: str | None = None
    sqm: float | None = None
    floor_raw: str | None = None
    floor: int | None = None
    address: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    lat: float | None = None
    lng: float | None = None
    phone: str | None = None
    amenities: dict[str, Any] = field(default_factory=dict)
    images: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    crawl_run_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Abstract base crawler
# ---------------------------------------------------------------------------

class BaseCrawler(abc.ABC):
    """
    Abstract base for all DiraScan source crawlers.

    Each crawler is responsible for:
      1. Setting up the browser/client session (Playwright, requests, etc.)
      2. Translating SearchFilters into source-specific query parameters
      3. Fetching paginated results and returning RawListing objects

    DB persistence is handled by the caller (API layer or CLI); crawlers
    never touch the database directly.
    """

    source_name: str  # must be set as a class attribute on every subclass

    def __init__(self) -> None:
        if not getattr(self, "source_name", None):
            raise TypeError(
                f"{self.__class__.__name__} must define `source_name` as a class attribute"
            )

    @abc.abstractmethod
    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        """
        Execute a scrape constrained by `filters`.

        Contract:
        - Must be async (Playwright and httpx are async-first).
        - Respect filters.max_results if set.
        - Do NOT raise on individual listing parse failures — log and skip.
        - Store the full source payload in raw_data for future reprocessing.
        """
        ...

    async def __aenter__(self) -> "BaseCrawler":
        """Override to set up browser/session resources."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Override to tear down browser/session resources."""
        pass
