"""add profile layout and image display permission

Revision ID: 4f8a2c7d91b3
Revises: 0addd5ed14cc
Create Date: 2026-11-13 16:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "4f8a2c7d91b3"
down_revision = "0addd5ed14cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profile_images",
        sa.Column(
            "is_displayable",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index("ix_profile_images_is_displayable", "profile_images", ["is_displayable"])
    op.create_table(
        "profile_layouts",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "draft_blocks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("published_blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "is_public",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "theme",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("profile_layouts")
    op.drop_index("ix_profile_images_is_displayable", table_name="profile_images")
    op.drop_column("profile_images", "is_displayable")
