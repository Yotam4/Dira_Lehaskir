"""Add composite indexes for common filter patterns

Revision ID: 002
Revises: 001
Create Date: 2026-03-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Explicit index on (source, source_id) to speed up upsert_listing lookups.
    # The UNIQUE constraint creates an implicit index but an explicit one makes
    # the intent clear and survives constraint renames.
    op.create_index(
        "idx_listing_sources_source_source_id",
        "listing_sources",
        ["source", "source_id"],
    )

    # Composite index for the most common combined filter: price + rooms range.
    op.create_index(
        "idx_listings_price_rooms",
        "listings",
        ["price", "rooms"],
    )

    # Run ANALYZE so the query planner has up-to-date statistics for the new indexes.
    op.execute("ANALYZE listings")
    op.execute("ANALYZE listing_sources")


def downgrade() -> None:
    op.drop_index("idx_listing_sources_source_source_id", table_name="listing_sources")
    op.drop_index("idx_listings_price_rooms", table_name="listings")
