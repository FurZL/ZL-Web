"""活动管理端点：创建、编辑、发布/取消、报名列表、签到管理。"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.user import User
from app.services.event import EventError
from app.services import event as event_service

router = APIRouter(
    prefix="/admin/events",
    tags=["admin"],
    dependencies=[Depends(require_permission_dep("event.manage"))],
)


class EventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    location: str | None = None
    starts_at: datetime
    ends_at: datetime
    capacity: int | None = Field(default=None, ge=1)
    registration_starts_at: datetime | None = None
    registration_ends_at: datetime | None = None
    publish_now: bool = False


class EventPatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = None
    registration_starts_at: datetime | None = None
    registration_ends_at: datetime | None = None


class EventStatusRequest(BaseModel):
    status: str  # draft / published / cancelled


def _parse_uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "无效的 ID"})


def _handle_error(exc: EventError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/")
async def list_events(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.event import Event

    rows = (await db.scalars(select(Event).order_by(Event.starts_at.desc()))).all()
    items = []
    for e in rows:
        reg_info = await event_service.list_registrations(db, e.id)
        items.append({
            **event_service._event_to_dict(e),
            "registered_count": reg_info["registered_count"],
            "waitlist_count": reg_info["waitlist_count"],
        })
    return ok({"items": items})


@router.post("/")
async def create_event(
    body: EventCreateRequest,
    user: User = Depends(require_permission_dep("event.manage")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.create_event(
            db,
            title=body.title,
            description=body.description,
            location=body.location,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            capacity=body.capacity,
            registration_starts_at=body.registration_starts_at,
            registration_ends_at=body.registration_ends_at,
            publish_now=body.publish_now,
            user=user,
        )
    except EventError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.get("/{event_id}")
async def get_event_detail(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        reg_info = await event_service.list_registrations(db, _parse_uuid(event_id))
        return ok(reg_info)
    except EventError as exc:
        raise _handle_error(exc)


@router.patch("/{event_id}")
async def update_event(
    event_id: str,
    body: EventPatchRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.update_event(
            db, _parse_uuid(event_id), **body.model_dump(exclude_unset=True)
        )
    except EventError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.patch("/{event_id}/status")
async def set_event_status(
    event_id: str,
    body: EventStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.set_event_status(db, _parse_uuid(event_id), body.status)
    except EventError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        await event_service.delete_event(db, _parse_uuid(event_id))
    except EventError as exc:
        raise _handle_error(exc)
    return ok({"message": "已删除"})


@router.get("/{event_id}/registrations")
async def list_registrations(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.list_registrations(db, _parse_uuid(event_id))
    except EventError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.post("/{event_id}/registrations/{registration_id}/checkin")
async def admin_checkin(
    event_id: str,
    registration_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.admin_checkin(
            db, _parse_uuid(event_id), _parse_uuid(registration_id)
        )
    except EventError as exc:
        raise _handle_error(exc)
    return ok(result)
