from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScrapeFilters(BaseModel):
    city: str = ""
    neighborhoods: list[str] = Field(default_factory=list)

    # Point + radius search
    lat: float | None = None
    lng: float | None = None
    radius_m: int | None = None        # metres

    # Drawn polygon (GeoJSON Polygon geometry JSON string)
    polygon_geojson: str | None = None

    price_min: int | None = None
    price_max: int | None = None
    rooms_min: float | None = None
    rooms_max: float | None = None
    max_results: int | None = None


class ScrapeRequest(BaseModel):
    sources: list[Literal["yad2", "madlan", "facebook"]] = Field(
        default=["yad2", "madlan", "facebook"]
    )
    filters: ScrapeFilters = Field(default_factory=ScrapeFilters)


class ScrapeRunResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    triggered_at: datetime
