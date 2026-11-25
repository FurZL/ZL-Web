"""课表相关 Schema。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Week = Annotated[int, Field(ge=1, le=53, strict=True)]
Clock = Annotated[str, Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]


class ScheduleSegments(BaseModel):
    """课表时段边界：上午 < 中午 < 下午 < 晚上，默认 12:00 / 14:00 / 18:00。"""

    model_config = ConfigDict(extra="forbid")

    noon: Clock = "12:00"
    afternoon: Clock = "14:00"
    evening: Clock = "18:00"

    @model_validator(mode="after")
    def ordered(self):
        def minutes(value: str) -> int:
            return int(value[:2]) * 60 + int(value[3:])

        if not minutes(self.noon) < minutes(self.afternoon) < minutes(self.evening):
            raise ValueError("时段边界必须按 中午 < 下午 < 晚上 的顺序排列")
        return self


class ScheduleTiming(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term_start: date | None = None
    first_start: Clock
    lesson_minutes: int = Field(ge=15, le=180, strict=True)
    break_minutes: int = Field(ge=0, le=180, strict=True)
    segments: ScheduleSegments = Field(default_factory=ScheduleSegments)
    periods: list[tuple[Clock, Clock]] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_period_order(self):
        from app.services.schedule_timing import validate_timing

        try:
            validate_timing(self.model_dump(mode="json"))
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(str(exc)) from exc
        return self


class CourseSlot(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(default="", max_length=255)
    weekday: int = Field(ge=0, le=6, description="0=周一 … 6=周日")
    lesson_start: int = Field(ge=1, le=24)
    lesson_end: int = Field(ge=1, le=24)
    weeks: list[Week] = Field(max_length=53)
    campus: str | None = Field(default=None, max_length=128)
    kind: Literal["course", "event"] = "course"

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("名称不能为空")
        return value.strip()

    @model_validator(mode="after")
    def valid_interval(self):
        if self.lesson_end < self.lesson_start:
            raise ValueError("结束节次不能早于开始节次")
        self.weeks = sorted(set(self.weeks))
        return self


class EditableSlot(CourseSlot):
    model_config = ConfigDict(extra="forbid")
    weeks: list[Week] = Field(min_length=1, max_length=53)


class ScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    slots: list[EditableSlot] = Field(default_factory=list, max_length=500)
    timing: ScheduleTiming | None = None


class ScheduleSlotsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slots: list[EditableSlot] = Field(max_length=500)
    revision: int = Field(ge=0, strict=True)


class ScheduleTimingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=0, strict=True)
    timing: ScheduleTiming


class CompareRequest(BaseModel):
    slots_a: list[CourseSlot] = Field(max_length=500)
    slots_b: list[CourseSlot] = Field(max_length=500)
    week: Week | None = None


class ScheduleUploadIntentRequest(BaseModel):
    filename: str
    size_bytes: int = Field(gt=0)


class ScheduleUploadCompleteRequest(BaseModel):
    bucket: str
    object_key: str
    original_name: str


class ScheduleVisibilityRequest(BaseModel):
    is_public: bool


class ScheduleMetaRequest(BaseModel):
    """课表架：重命名与存档/恢复。至少提供一个字段。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    original_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_archived: bool | None = None

    @model_validator(mode="after")
    def needs_one_change(self):
        if self.original_name is None and self.is_archived is None:
            raise ValueError("请提供课表名称或存档状态")
        return self


class ScheduleOrderRequest(BaseModel):
    """课表架拖动排序：提交用户全部课表的完整 id 顺序。"""

    model_config = ConfigDict(extra="forbid")

    ids: list[UUID] = Field(default_factory=list, max_length=200)


class ScheduleGroupCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)
    join_mode: Literal["open", "approval"] = "open"


class ScheduleGroupJoinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=6, max_length=12)


class ScheduleGroupUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=50)
    join_mode: Literal["open", "approval"] | None = None

    @model_validator(mode="after")
    def needs_change(self):
        if self.name is None and self.join_mode is None:
            raise ValueError("请提供群组名称或加入方式")
        return self


class ScheduleGroupScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: UUID | None = None


class MealWindow(BaseModel):
    date_from: date
    date_to: date
    daily_start: Clock = "11:30"
    daily_end: Clock = "13:30"
    duration_minutes: int = Field(default=60, ge=15, le=1440)
    buffer_minutes: int = Field(default=0, ge=0, le=90)

    @model_validator(mode="after")
    def validate_window(self):
        def minute(clock):
            return int(clock[:2]) * 60 + int(clock[3:])

        if not 0 <= (self.date_to - self.date_from).days <= 30:
            raise ValueError("请选择 1–31 天的日期范围")
        if minute(self.daily_end) - minute(self.daily_start) < self.duration_minutes:
            raise ValueError("每天的可约时间不足以容纳这顿饭")
        return self


class AppointmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schedule_id: UUID
    window: MealWindow
    invitee_username: str = Field(min_length=1, max_length=64)
    title: str = Field(default="一起吃饭", min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)


class FixedAppointmentCreateRequest(BaseModel):
    """从课表对比的空闲时段直接约一个具体周次的时间。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schedule_id: UUID
    invitee_username: str = Field(min_length=1, max_length=64)
    title: str = Field(default="一起见面", min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)
    week: int = Field(ge=1, le=53)
    weekday: int = Field(ge=0, le=6)
    lesson_start: int = Field(ge=1, le=24)
    lesson_end: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def validate_lessons(self):
        if self.lesson_end < self.lesson_start:
            raise ValueError("结束节次不能早于开始节次")
        return self


class AppointmentResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: bool
    schedule_id: UUID | None = None

    @model_validator(mode="after")
    def acceptance_needs_calendar(self):
        if self.accepted and not self.schedule_id:
            raise ValueError("请选择自己的课表")
        return self


class CalendarEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_times(self):
        if not self.starts_at.tzinfo or not self.ends_at.tzinfo or self.starts_at >= self.ends_at:
            raise ValueError("请填写含时区且依次递增的起止时间")
        return self


class AppointmentChoicesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[str] = Field(max_length=5)


class AppointmentConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=32)
