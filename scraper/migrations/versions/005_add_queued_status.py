"""Add 'queued' status to scrape_runs and worker-polling indexes.

The scraper now runs as a separate worker that polls scrape_runs for jobs the
API enqueues. Jobs start life as 'queued'; the original CHECK constraint only
allowed ('running', 'completed', 'failed').

Revision ID: 005
Revises: 004
Create Date: 2026-06-05
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_scrape_runs_status", "scrape_runs", type_="check")
    op.create_check_constraint(
        "ck_scrape_runs_status",
        "scrape_runs",
        "status IN ('queued', 'running', 'completed', 'failed')",
    )

    # Partial indexes: the worker polls only queued rows (FIFO) and the
    # stale-run recovery sweep scans only running rows.
    op.execute(
        "CREATE INDEX idx_scrape_runs_queued "
        "ON scrape_runs (triggered_at ASC) WHERE status = 'queued'"
    )
    op.execute(
        "CREATE INDEX idx_scrape_runs_running "
        "ON scrape_runs (triggered_at ASC) WHERE status = 'running'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_scrape_runs_running")
    op.execute("DROP INDEX IF EXISTS idx_scrape_runs_queued")
    op.drop_constraint("ck_scrape_runs_status", "scrape_runs", type_="check")
    op.create_check_constraint(
        "ck_scrape_runs_status",
        "scrape_runs",
        "status IN ('running', 'completed', 'failed')",
    )
