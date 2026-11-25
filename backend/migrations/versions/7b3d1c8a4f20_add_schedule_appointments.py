"""add one-to-one schedule appointments"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "7b3d1c8a4f20"
down_revision = "4f8a2c7d91b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organizer_schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitee_schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("duration_lessons", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("candidates_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selected_candidate_id", sa.String(length=32), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_appointments_organizer_id", "schedule_appointments", ["organizer_id"])
    op.create_index("ix_schedule_appointments_invitee_id", "schedule_appointments", ["invitee_id"])
    op.create_index("ix_schedule_appointments_status", "schedule_appointments", ["status"])

    op.create_table(
        "schedule_appointment_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("choices_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confirmed_candidate_id", sa.String(length=32), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["schedule_appointments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_appointment_participants_appointment_id", "schedule_appointment_participants", ["appointment_id"])
    op.create_index("ix_schedule_appointment_participants_user_id", "schedule_appointment_participants", ["user_id"])
    op.create_unique_constraint(
        "uq_schedule_appointment_participant", "schedule_appointment_participants", ["appointment_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_schedule_appointment_participant", "schedule_appointment_participants", type_="unique")
    op.drop_index("ix_schedule_appointment_participants_user_id", table_name="schedule_appointment_participants")
    op.drop_index("ix_schedule_appointment_participants_appointment_id", table_name="schedule_appointment_participants")
    op.drop_table("schedule_appointment_participants")
    op.drop_index("ix_schedule_appointments_status", table_name="schedule_appointments")
    op.drop_index("ix_schedule_appointments_invitee_id", table_name="schedule_appointments")
    op.drop_index("ix_schedule_appointments_organizer_id", table_name="schedule_appointments")
    op.drop_table("schedule_appointments")
