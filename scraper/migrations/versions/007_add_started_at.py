"""Add scrape_runs.started_at (claim time) for accurate stale-run recovery.

The worker flips a run to 'running' and stamps started_at at claim time. Stale
recovery compares against started_at (falling back to triggered_at for any
legacy running row), so a job that merely waited a long time in the queue is no
longer mistaken for a crashed, long-running one.

Revision ID: 007
Revises: 006
Create Date: 2026-06-05
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scrape_runs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scrape_runs", "started_at")
