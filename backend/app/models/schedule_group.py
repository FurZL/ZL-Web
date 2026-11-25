"""课表对比群组模型。

群组是私密的课搭子圈：成员加入后选择一份自己的课表共享给群，
群页面逐人展示与我的忙闲对比。群组本身不公开任何课表。
"""

from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class ScheduleGroup(TimestampMixin, Base):
    __tablename__ = "schedule_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    join_mode: Mapped[str] = mapped_column(String(16), default="open", nullable=False)


class ScheduleGroupMember(TimestampMixin, Base):
    __tablename__ = "schedule_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_schedule_group_member"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    # 成员选择共享给本群的课表；为空表示还没共享
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
