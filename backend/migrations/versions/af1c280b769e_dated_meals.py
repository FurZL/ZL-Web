"""Join the upstream auth and local schedule heads; add dated meal calendars."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "af1c280b769e"
down_revision = ("2b7e4c9d1a60", "7b3d1c8a4f20")
branch_labels = None
depends_on = None


def upgrade():
    # A lesson number has no unique date. Never silently convert a prototype booking.
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM schedule_appointments) THEN
        RAISE EXCEPTION 'Archive or explicitly convert existing lesson-based appointments first';
        END IF; END $$""")
    for name in ("invitee_id", "invitee_schedule_id", "organizer_schedule_id", "duration_lessons"):
        op.drop_column("schedule_appointments", name)
    op.add_column("schedule_appointments", sa.Column("preferences", JSONB(), nullable=False))
    op.add_column("schedule_appointment_participants", sa.Column("schedule_id", UUID()))
    op.add_column("schedule_appointment_participants", sa.Column("calendar", JSONB()))
    op.create_table(
        "calendar_events",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "owner_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("appointment_id", UUID(), sa.ForeignKey("schedule_appointments.id")),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("appointment_id", "owner_id", name="uq_event_appointment_owner"),
    )
    op.create_index("ix_calendar_events_owner_id", "calendar_events", ["owner_id"])


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM schedule_appointments)
        OR EXISTS (SELECT 1 FROM calendar_events) THEN
        RAISE EXCEPTION 'Archive dated appointments and events before downgrade'; END IF; END $$""")
    op.drop_table("calendar_events")
    op.drop_column("schedule_appointment_participants", "calendar")
    op.drop_column("schedule_appointment_participants", "schedule_id")
    op.drop_column("schedule_appointments", "preferences")
    for name in ("invitee_id", "invitee_schedule_id", "organizer_schedule_id"):
        op.add_column("schedule_appointments", sa.Column(name, UUID(), nullable=False))
    op.create_index("ix_schedule_appointments_invitee_id", "schedule_appointments", ["invitee_id"])
    op.add_column(
        "schedule_appointments", sa.Column("duration_lessons", sa.Integer(), nullable=False)
    )
