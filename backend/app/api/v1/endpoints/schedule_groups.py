"""课表对比群组端点。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import error_to_http, ok, parse_uuid
from app.core.database import get_db
from app.models.user import User
from app.schemas.schedule import (
    ScheduleGroupCreateRequest,
    ScheduleGroupJoinRequest,
    ScheduleGroupScheduleRequest,
    ScheduleGroupUpdateRequest,
    GroupAvailabilityRequest,
    GroupFixedInviteRequest,
)
from app.services import schedule_group as group_service
from app.services.image import ImageError
from app.services.schedule_config import require_schedule_feature
from app.services import schedule_group_meeting

router = APIRouter(prefix="/schedule/groups", tags=["schedule-groups"])


@router.post("/{group_id}/availability")
async def group_availability(group_id: str, body: GroupAvailabilityRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        return ok(await schedule_group_meeting.availability(db, user, parse_uuid(group_id), body))
    except ImageError as exc:
        raise error_to_http(exc)


@router.post("/{group_id}/appointments", status_code=201)
async def group_appointment(group_id: str, body: GroupFixedInviteRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await require_schedule_feature(db, "fixed_invite_enabled")
    try:
        return ok(await schedule_group_meeting.create_invitation(db, user, parse_uuid(group_id), body))
    except ImageError as exc:
        raise error_to_http(exc)


@router.get("")
async def list_groups(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ok(await group_service.list_groups(db, user))


@router.post("", status_code=201)
async def create_group(
    body: ScheduleGroupCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_schedule_feature(db, "group_join_enabled")
    try:
        return ok(await group_service.create_group(db, user, body))
    except ImageError as exc:
        raise error_to_http(exc)


@router.post("/join")
async def join_group(
    body: ScheduleGroupJoinRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_schedule_feature(db, "group_join_enabled")
    try:
        return ok(await group_service.join_group(db, user, body.code))
    except ImageError as exc:
        raise error_to_http(exc)


@router.get("/{group_id}")
async def group_detail(
    group_id: str,
    week: int | None = Query(default=None, ge=1, le=53),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return ok(await group_service.group_detail(db, user, parse_uuid(group_id), week))
    except ImageError as exc:
        raise error_to_http(exc)


@router.patch("/{group_id}")
async def update_group(
    group_id: str,
    body: ScheduleGroupUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return ok(await group_service.update_group(db, user, parse_uuid(group_id), body))
    except ImageError as exc:
        raise error_to_http(exc)


@router.delete("/{group_id}")
async def delete_group(
    group_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    try:
        await group_service.delete_group(db, user, parse_uuid(group_id))
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"message": "群组已解散"})


@router.put("/{group_id}/schedule")
async def set_group_schedule(
    group_id: str,
    body: ScheduleGroupScheduleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return ok(
            await group_service.set_group_schedule(db, user, parse_uuid(group_id), body.schedule_id)
        )
    except ImageError as exc:
        raise error_to_http(exc)


@router.post("/{group_id}/members/{member_user_id}/approve")
async def approve_member(
    group_id: str,
    member_user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return ok(
            await group_service.approve_member(
                db, user, parse_uuid(group_id), parse_uuid(member_user_id)
            )
        )
    except ImageError as exc:
        raise error_to_http(exc)


@router.post("/{group_id}/members/{member_user_id}/reject")
async def reject_member(
    group_id: str,
    member_user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await group_service.reject_member(
            db, user, parse_uuid(group_id), parse_uuid(member_user_id)
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"message": "已拒绝入群申请"})


@router.delete("/{group_id}/members/{member_user_id}")
async def remove_member(
    group_id: str,
    member_user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await group_service.remove_member(
            db, user, parse_uuid(group_id), parse_uuid(member_user_id)
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"message": "已退出群组"})
