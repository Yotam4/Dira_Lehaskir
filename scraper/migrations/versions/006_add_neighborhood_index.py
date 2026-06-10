"""Add neighborhood indexes for the /neighborhoods endpoint and ILIKE search.

Revision ID: 006
Revises: 005
Create Date: 2026-06-05
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trigram index accelerates ILIKE on neighborhood (and the city filter).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX idx_listings_neighborhood_trgm "
        "ON listings USING gin (neighborhood gin_trgm_ops)"
    )
    # Btree covers SELECT DISTINCT neighborhood WHERE city ... ORDER BY neighborhood.
    op.create_index(
        "idx_listings_city_neighborhood",
        "listings",
        ["city", "neighborhood"],
    )


def downgrade() -> None:
    op.drop_index("idx_listings_city_neighborhood", table_name="listings")
    op.execute("DROP INDEX IF EXISTS idx_listings_neighborhood_trgm")
