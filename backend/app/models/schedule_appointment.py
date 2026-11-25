"""预约、参与者与一次性日程。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class ScheduleAppointment(TimestampMixin, Base):
    __tablename__ = "schedule_appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organizer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    candidates_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    selected_candidate_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScheduleAppointmentParticipant(TimestampMixin, Base):
    __tablename__ = "schedule_appointment_participants"
    __table_args__ = (
        UniqueConstraint("appointment_id", "user_id", name="uq_schedule_appointment_participant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schedule_appointments.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    calendar: Mapped[dict | None] = mapped_column(JSONB)
    choices_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    confirmed_candidate_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notice: Mapped[str | None] = mapped_column("note", Text, nullable=True)


class CalendarEvent(TimestampMixin, Base):
    """一次性安排归属于账号，换课表也不会丢失。"""

    __tablename__ = "calendar_events"
    __table_args__ = (
        UniqueConstraint("appointment_id", "owner_id", name="uq_event_appointment_owner"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("schedule_appointments.id"))
    title: Mapped[str] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=0)
