"""Add FK constraint on listing_sources and CHECK constraints on listings.

Revision ID: 003
Revises: 002
Create Date: 2026-03-25
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FK: listing_sources.listing_id → listings.id (with cascade delete)
    op.create_foreign_key(
        "fk_listing_sources_listing_id",
        "listing_sources",
        "listings",
        ["listing_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # CHECK constraints: prevent non-positive numeric values
    op.create_check_constraint(
        "ck_listings_price_positive", "listings", "price IS NULL OR price > 0"
    )
    op.create_check_constraint(
        "ck_listings_rooms_positive", "listings", "rooms IS NULL OR rooms > 0"
    )
    op.create_check_constraint(
        "ck_listings_sqm_positive", "listings", "sqm IS NULL OR sqm > 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_listings_sqm_positive", "listings", type_="check")
    op.drop_constraint("ck_listings_rooms_positive", "listings", type_="check")
    op.drop_constraint("ck_listings_price_positive", "listings", type_="check")
    op.drop_constraint("fk_listing_sources_listing_id", "listing_sources", type_="foreignkey")
