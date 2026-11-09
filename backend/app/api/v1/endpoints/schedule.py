"""课表端点：上传、解析、查询、对比、删除。

上传走预签名直传；upload-complete 时后端下载文件并解析（ICS/TXT）。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import ok
from app.core.database import get_db
from app.models.user import User
from app.schemas.schedule import (
    CompareRequest,
    ScheduleUploadCompleteRequest,
    ScheduleUploadIntentRequest,
)
from app.services import schedule_service
from app.services.image import ImageError
from app.services.schedule import compare as compare_service
from app.services.schedule import CourseSlot

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _parse_uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "无效的 ID"})


def _img_error(exc: ImageError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.get("/mine")
async def my_schedules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await schedule_service.get_my_schedules(db, user)
    return ok(result)


@router.post("/upload-intent")
async def upload_intent(
    body: ScheduleUploadIntentRequest,
    user: User = Depends(get_current_user),
):
    try:
        intent = await schedule_service.create_schedule_upload_intent(
            user=user, filename=body.filename, size_bytes=body.size_bytes
        )
    except ImageError as exc:
        raise _img_error(exc)
    return ok(intent)


@router.post("/upload-complete")
async def upload_complete(
    body: ScheduleUploadCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        schedule = await schedule_service.complete_schedule_upload(
            db,
            user=user,
            object_key=body.object_key,
            bucket=body.bucket,
            original_name=body.original_name,
        )
    except ImageError as exc:
        raise _img_error(exc)
    result = await schedule_service.get_schedule(db, schedule.id, user)
    return ok(result)


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_service.get_schedule(db, _parse_uuid(schedule_id), user)
    except ImageError as exc:
        raise _img_error(exc)
    return ok(result)


@router.post("/compare")
async def compare(body: CompareRequest, user: User = Depends(get_current_user)):
    slots_a = [CourseSlot(**s.model_dump()) for s in body.slots_a]
    slots_b = [CourseSlot(**s.model_dump()) for s in body.slots_b]
    return ok(compare_service(slots_a, slots_b))


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await schedule_service.delete_schedule(db, _parse_uuid(schedule_id), user)
    except ImageError as exc:
        raise _img_error(exc)
    return ok({"message": "已删除"})