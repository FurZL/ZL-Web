"""add user_third_parties table

Revision ID: e7f3a91b2d44
Revises: 4f8a2c7d91b3
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e7f3a91b2d44"
down_revision = "4f8a2c7d91b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_third_parties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=128), nullable=False),
        sa.Column("unionid", sa.String(length=128), nullable=True),
        sa.Column("access_token", sa.String(length=512), nullable=True),
        sa.Column("refresh_token", sa.String(length=512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_profile", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_third_parties_provider_identity",
        "user_third_parties",
        ["provider", "provider_user_id"],
        unique=True,
    )
    op.create_index(
        "ix_user_third_parties_provider_unionid",
        "user_third_parties",
        ["provider", "unionid"],
        unique=False,
    )
    op.create_index(
        "ix_user_third_parties_user_id",
        "user_third_parties",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_third_parties_user_id", table_name="user_third_parties")
    op.drop_index("ix_user_third_parties_provider_unionid", table_name="user_third_parties")
    op.drop_index("ix_user_third_parties_provider_identity", table_name="user_third_parties")
    op.drop_table("user_third_parties")

