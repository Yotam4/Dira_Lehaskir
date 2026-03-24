from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    original_url: str | None
    title: str
    description: str | None
    price: int | None
    rooms: float | None
    sqm: float | None
    floor: int | None
    address: str | None
    city: str
    neighborhood: str | None
    lat: float | None
    lng: float | None
    amenities: dict[str, Any]
    images: list[str]
    scraped_at: datetime
    created_at: datetime


class ListingsPage(BaseModel):
    items: list[ListingResponse]
    total: int
    page: int
    page_size: int
