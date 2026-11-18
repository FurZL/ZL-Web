"""add user legal consent record

Revision ID: 2b7e4c9d1a60
Revises: e7f3a91b2d44
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "2b7e4c9d1a60"
down_revision = "e7f3a91b2d44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_version", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("privacy_version", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column("legal_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "legal_accepted_at")
    op.drop_column("users", "privacy_version")
    op.drop_column("users", "terms_version")
