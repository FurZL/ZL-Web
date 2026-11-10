"""课表服务：上传意图、上传完成（下载+解析+落库）、查询、删除。

- 课表私有文件存 private/schedules/{user_id}/ 前缀。
- 上传流程复用预签名直传；upload-complete 时后端下载文件、解析、落库。
- ICS/TXT 解析很快，同步解析即可；PDF 占位抛出明确错误。
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import StoredObject
from app.models.schedule import Schedule
from app.models.user import User
from app.providers.factory import get_storage_provider
from app.services.image import ImageError
from app.services.schedule import ScheduleParseError, parse_schedule


def _new_schedule_object_key(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    token = secrets.token_hex(16)
    return f"private/schedules/{user_id}/{now.year:04d}/{now.month:02d}/{token}"


async def create_schedule_upload_intent(
    *, user: User, filename: str, size_bytes: int
) -> dict:
    # 大小上限：课表文件通常远小于一般图片，这里仍用全局上限
    if size_bytes <= 0 or size_bytes > settings.upload_max_bytes:
        raise ImageError("FILE_TOO_LARGE", "文件大小超限")

    object_key = _new_schedule_object_key(user.id)
    storage = get_storage_provider()
    presign = await storage.presign_upload(
        bucket=storage.bucket,
        object_key=object_key,
        content_type="application/octet-stream",
        max_bytes=size_bytes,
        expires_in=settings.private_url_ttl_seconds,
    )
    return {
        "storage_provider": settings.storage_provider,
        "bucket": storage.bucket,
        "object_key": object_key,
        "upload_url": presign.url,
        "expires_in": presign.expires_in,
    }


async def complete_schedule_upload(
    db: AsyncSession,
    *,
    user: User,
    object_key: str,
    bucket: str,
    original_name: str,
) -> Schedule:
    valid_prefix = f"private/schedules/{user.id}/"
    if not object_key.startswith(valid_prefix):
        raise ImageError("INVALID_KEY", "无效的对象 Key")

    storage = get_storage_provider()
    head = await storage.head_object(bucket or storage.bucket, object_key)
    if not head.exists:
        raise ImageError("OBJECT_NOT_FOUND", "对象不存在，请重新上传")

    # 下载文件内容
    data = await storage.get_object_bytes(bucket or storage.bucket, object_key)

    # 解析
    try:
        parsed = parse_schedule(data, original_name)
    except ScheduleParseError as exc:
        raise ImageError("PARSE_FAILED", exc.message)

    # 落库 StoredObject + Schedule
    stored = StoredObject(
        provider=settings.storage_provider,
        bucket=bucket or storage.bucket,
        object_key=object_key,
        visibility="private",
        mime_type=None,
        size_bytes=head.size_bytes,
        processing_status="ready",
        created_by=user.id,
    )
    db.add(stored)
    await db.flush()

    schedule = Schedule(
        owner_id=user.id,
        stored_object_id=stored.id,
        original_name=original_name,
        format=parsed["format"],
        parsed_json={"slots": parsed["slots"]},
        is_public=False,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_my_schedules(db: AsyncSession, user: User) -> dict:
    schedules = (
        await db.scalars(
            select(Schedule).where(Schedule.owner_id == user.id).order_by(Schedule.created_at.desc())
        )
    ).all()
    return {"items": [await _schedule_to_dict(s) for s in schedules]}


async def get_schedule(db: AsyncSession, schedule_id: uuid.UUID, user: User) -> dict:
    s = await db.get(Schedule, schedule_id)
    if s is None:
        raise ImageError("NOT_FOUND", "课表不存在", 404)
    # 私有课表仅本人可见；公开课表任何人可看
    if not s.is_public and s.owner_id != user.id:
        raise ImageError("FORBIDDEN", "无权访问该课表", 403)
    return await _schedule_to_dict(s)


async def delete_schedule(db: AsyncSession, schedule_id: uuid.UUID, user: User) -> None:
    s = await db.get(Schedule, schedule_id)
    if s is None or s.owner_id != user.id:
        raise ImageError("NOT_FOUND", "课表不存在", 404)
    stored = await db.get(StoredObject, s.stored_object_id) if s.stored_object_id else None
    if stored:
        try:
            storage = get_storage_provider()
            await storage.delete_object(stored.bucket, stored.object_key)
        except Exception:
            pass
        db.delete(stored)
    db.delete(s)
    await db.commit()


async def get_public_schedule_by_owner(db: AsyncSession, owner_id: uuid.UUID) -> dict:
    """获取某用户的公开课表。仅返回最近一条已公开的课表。"""
    s = (
        await db.scalars(
            select(Schedule)
            .where(
                Schedule.owner_id == owner_id,
                Schedule.is_public.is_(True),
            )
            .order_by(Schedule.created_at.desc())
            .limit(1)
        )
    ).first()
    if s is None:
        raise ImageError("NOT_FOUND", "该用户没有公开的课表", 404)
    return await _schedule_to_dict(s)


async def get_public_schedule_by_username(db: AsyncSession, username: str) -> dict:
    """按用户名获取公开课表，附带公开的用户信息（供对比使用）。"""
    from app.models.user import User

    u = (
        await db.scalars(select(User).where(User.username == username).limit(1))
    ).first()
    if u is None:
        raise ImageError("NOT_FOUND", "用户不存在", 404)
    s = (
        await db.scalars(
            select(Schedule)
            .where(Schedule.owner_id == u.id, Schedule.is_public.is_(True))
            .order_by(Schedule.created_at.desc())
            .limit(1)
        )
    ).first()
    if s is None:
        raise ImageError("NOT_FOUND", "该用户没有公开的课表", 404)
    data = await _schedule_to_dict(s)
    data["owner"] = {
        "id": str(u.id),
        "username": u.username,
        "display_name": u.display_name,
    }
    return data


async def set_schedule_visibility(
    db: AsyncSession, schedule_id: uuid.UUID, is_public: bool, user: User
) -> dict:
    s = await db.get(Schedule, schedule_id)
    if s is None or s.owner_id != user.id:
        raise ImageError("NOT_FOUND", "课表不存在", 404)
    s.is_public = is_public
    await db.commit()
    await db.refresh(s)
    return await _schedule_to_dict(s)


async def _schedule_to_dict(s: Schedule) -> dict:
    return {
        "id": str(s.id),
        "original_name": s.original_name,
        "format": s.format,
        "slots": s.parsed_json.get("slots", []),
        "is_public": s.is_public,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
    }