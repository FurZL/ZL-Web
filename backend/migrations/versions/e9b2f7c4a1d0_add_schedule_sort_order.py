"""add schedule shelf sort order

Revision ID: e9b2f7c4a1d0
Revises: c4a91e7d2b60
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e9b2f7c4a1d0"
down_revision = "c4a91e7d2b60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """课表架拖动排序；旧课表统一 0，仍按创建时间倒序排列。"""
    op.add_column(
        "schedules",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("schedules", "sort_order")
