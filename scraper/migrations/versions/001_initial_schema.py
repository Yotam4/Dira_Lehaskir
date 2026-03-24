"""Initial schema — listings, listing_sources, scrape_runs

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS MUST be created before any Geometry columns
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("original_url", sa.Text),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("price", sa.Integer),
        sa.Column("rooms", sa.Numeric(4, 1)),
        sa.Column("sqm", sa.Numeric(6, 1)),
        sa.Column("floor", sa.SmallInteger),
        sa.Column("address", sa.Text),
        sa.Column("city", sa.Text, nullable=False),
        sa.Column("neighborhood", sa.Text),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry("POINT", srid=4326, spatial_index=False),
        ),
        sa.Column("amenities", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("images", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("raw_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # GIST index for spatial queries (ST_DWithin, ST_Within)
    op.create_index(
        "idx_listings_location",
        "listings",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index("idx_listings_source", "listings", ["source"])
    op.create_index("idx_listings_city", "listings", ["city"])
    op.create_index("idx_listings_price", "listings", ["price"])
    op.create_index("idx_listings_rooms", "listings", ["rooms"])
    op.create_index(
        "idx_listings_scraped_at",
        "listings",
        [sa.text("scraped_at DESC")],
    )

    # updated_at auto-update trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_listings_updated_at
            BEFORE UPDATE ON listings
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    op.create_table(
        "listing_sources",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("source_id", sa.Text, nullable=False),
        sa.Column("original_url", sa.Text),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("source", "source_id", name="uq_listing_sources_source_id"),
    )
    op.create_index(
        "idx_listing_sources_listing_id",
        "listing_sources",
        ["listing_id"],
    )

    op.create_table(
        "scrape_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="running",
        ),
        sa.Column("sources", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("filters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("listings_found", sa.Integer),
        sa.Column("listings_new", sa.Integer),
        sa.Column("error_message", sa.Text),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_scrape_runs_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("scrape_runs")
    op.drop_table("listing_sources")
    op.execute("DROP TRIGGER IF EXISTS trg_listings_updated_at ON listings")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column")
    op.drop_table("listings")
    op.execute("DROP EXTENSION IF EXISTS postgis")
