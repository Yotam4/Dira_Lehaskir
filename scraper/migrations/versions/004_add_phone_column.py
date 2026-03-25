"""Add phone column to listings.

Revision ID: 004
Revises: 003
Create Date: 2026-03-25
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("phone", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "phone")
