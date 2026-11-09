"""活动、公告相关 Schema。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime
    ends_at: datetime
    capacity: int | None = None
    registration_starts_at: datetime | None = None
    registration_ends_at: datetime | None = None


class EventOut(EventCreate):
    id: uuid.UUID
    status: str


class AnnouncementOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    is_pinned: bool
    published_at: datetime | None