"""add schedule archive flag

Revision ID: c4a91e7d2b60
Revises: af1c280b769e
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c4a91e7d2b60"
down_revision = "af1c280b769e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """课表架：已存档的课表留在历史列表，但不再参与公开读取。"""
    op.add_column(
        "schedules",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("schedules", "is_archived")
