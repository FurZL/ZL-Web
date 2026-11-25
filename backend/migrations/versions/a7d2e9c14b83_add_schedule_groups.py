"""add schedule groups

Revision ID: a7d2e9c14b83
Revises: e9b2f7c4a1d0
Create Date: 2026-11-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7d2e9c14b83"
down_revision = "e9b2f7c4a1d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("join_mode", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedule_groups_code"), "schedule_groups", ["code"], unique=True)
    op.create_index(op.f("ix_schedule_groups_owner_id"), "schedule_groups", ["owner_id"])

    op.create_table(
        "schedule_group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="member"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_schedule_group_member"),
    )
    op.create_index(
        op.f("ix_schedule_group_members_group_id"), "schedule_group_members", ["group_id"]
    )
    op.create_index(
        op.f("ix_schedule_group_members_user_id"), "schedule_group_members", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_schedule_group_members_user_id"), table_name="schedule_group_members")
    op.drop_index(op.f("ix_schedule_group_members_group_id"), table_name="schedule_group_members")
    op.drop_table("schedule_group_members")
    op.drop_index(op.f("ix_schedule_groups_owner_id"), table_name="schedule_groups")
    op.drop_index(op.f("ix_schedule_groups_code"), table_name="schedule_groups")
    op.drop_table("schedule_groups")
