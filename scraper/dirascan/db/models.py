from __future__ import annotations

import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Listing(Base):
    __tablename__ = "listings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(20), nullable=False)
    original_url = Column(Text)
    title = Column(Text, nullable=False)
    description = Column(Text)
    price = Column(Integer)                      # ILS
    rooms = Column(Numeric(4, 1))                # 3.5 חדרים is common in Israel
    sqm = Column(Numeric(6, 1))
    floor = Column(SmallInteger)
    address = Column(Text)
    city = Column(Text, nullable=False)
    neighborhood = Column(Text)
    location = Column(Geometry("POINT", srid=4326))   # PostGIS point (lng, lat)
    amenities = Column(JSONB, nullable=False, default=dict)
    images = Column(JSONB, nullable=False, default=list)
    raw_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    scraped_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    @property
    def lat(self) -> float | None:
        if self.location is None:
            return None
        return to_shape(self.location).y

    @property
    def lng(self) -> float | None:
        if self.location is None:
            return None
        return to_shape(self.location).x

    def __repr__(self) -> str:
        return f"<Listing id={self.id} source={self.source} city={self.city} price={self.price}>"


class ListingSource(Base):
    """
    Deduplication table — one canonical listing can appear on multiple sources.
    The UNIQUE(source, source_id) constraint prevents re-inserting the same post.
    """

    __tablename__ = "listing_sources"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    listing_id = Column(PG_UUID(as_uuid=True), nullable=False)
    source = Column(String(20), nullable=False)
    source_id = Column(Text, nullable=False)
    original_url = Column(Text)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<ListingSource source={self.source} source_id={self.source_id}>"


class ScrapeRun(Base):
    """Audit log for each on-demand scrape trigger."""

    __tablename__ = "scrape_runs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    triggered_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True))
    status = Column(
        String(20),
        nullable=False,
        default="running",
    )
    sources = Column(ARRAY(Text), nullable=False)
    filters = Column(JSONB, nullable=False, default=dict)
    listings_found = Column(Integer)
    listings_new = Column(Integer)
    error_message = Column(Text)

    def __repr__(self) -> str:
        return f"<ScrapeRun id={self.id} status={self.status}>"
