"""活动端点：列表、详情、报名、取消、签到。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import error_to_http, ok, parse_uuid
from app.core.database import get_db
from app.models.user import User
from app.services.event import EventError
from app.services import event as event_service

router = APIRouter(prefix="/events", tags=["events"])


class RegisterRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=128)


@router.get("/")
async def list_events(
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公开活动列表（登录后含自己的报名状态）。"""
    try:
        result = await event_service.list_events(db, user)
    except EventError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.get_event(db, parse_uuid(event_id), user)
    except EventError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/{event_id}/register")
async def register_event(
    event_id: str,
    body: RegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.register(
            db, parse_uuid(event_id), user, body.idempotency_key
        )
    except EventError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.delete("/{event_id}/register")
async def cancel_registration(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.cancel_registration(db, parse_uuid(event_id), user)
    except EventError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/{event_id}/checkin")
async def checkin(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await event_service.checkin(db, parse_uuid(event_id), user)
    except EventError as exc:
        raise error_to_http(exc)
    return ok(result)
