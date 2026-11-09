"""课表相关 Schema。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CourseSlot(BaseModel):
    name: str
    location: str
    weekday: int = Field(ge=0, le=6, description="0=周一 … 6=周日")
    lesson_start: int = Field(ge=1, le=12)
    lesson_end: int = Field(ge=1, le=12)
    weeks: list[int]
    campus: str | None = None


class CompareRequest(BaseModel):
    slots_a: list[CourseSlot]
    slots_b: list[CourseSlot]


class CompareResult(BaseModel):
    same_classroom: list[CourseSlot]
    both_free: list[CourseSlot]
    overlaps: list[CourseSlot]


class ScheduleJobOut(BaseModel):
    job_id: str
    status: str
    error: str | None = None


class ScheduleUploadIntentRequest(BaseModel):
    filename: str
    size_bytes: int = Field(gt=0)


class ScheduleUploadCompleteRequest(BaseModel):
    bucket: str
    object_key: str
    original_name: str


class ScheduleOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    is_public: bool
    expires_at: datetime | None
    parsed_json: dict