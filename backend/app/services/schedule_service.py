"""课表服务：上传意图、上传完成（下载+解析+落库）、查询、删除。

- 课表私有文件存 private/schedules/{user_id}/ 前缀。
- 上传流程复用预签名直传；upload-complete 时后端下载文件、解析、落库。
- ICS/TXT 解析很快，同步解析即可；PDF 占位抛出明确错误。
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import StoredObject
from app.models.schedule import Schedule
from app.models.user import User
from app.providers.factory import get_storage_provider
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleMetaRequest,
    ScheduleOrderRequest,
    ScheduleSlotsRequest,
    ScheduleTimingRequest,
)
from app.services.image import ImageError
from app.services.schedule import ScheduleParseError, parse_schedule
from app.services.schedule_timing import (
    DEFAULT_PERIOD_COUNT,
    MAX_PERIOD_COUNT,
    default_timing,
    normalize_timing,
)

logger = logging.getLogger(__name__)


def _required_period_count(slots: list[dict]) -> int:
    return max((int(slot.get("lesson_end", 0)) for slot in slots), default=0)


def _timing_for_slots(slots: list[dict]) -> dict:
    count = max(DEFAULT_PERIOD_COUNT, _required_period_count(slots))
    if count > MAX_PERIOD_COUNT:
        raise ImageError("TOO_MANY_LESSONS", f"课表最多支持 {MAX_PERIOD_COUNT} 节", 422)
    try:
        return default_timing(count)
    except ValueError as exc:
        raise ImageError(
            "TIMING_REQUIRED",
            "课程节次超出默认作息的当天时间范围，请先设置更早的开始时间或更短的课间隔",
            422,
        ) from exc


def _validate_slots_fit_timing(slots: list[dict], timing: dict) -> None:
    required = _required_period_count(slots)
    available = len(timing["periods"])
    if required > available:
        raise ImageError(
            "TIMING_TOO_SHORT",
            f"当前作息只有 {available} 节，但课程使用了第 {required} 节，请先增加节数",
            422,
        )


def _new_schedule_object_key(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    token = secrets.token_hex(16)
    return f"private/schedules/{user_id}/{now.year:04d}/{now.month:02d}/{token}"


async def create_schedule_upload_intent(*, user: User, filename: str, size_bytes: int) -> dict:
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
        parsed_json={"slots": parsed["slots"], "timing": _timing_for_slots(parsed["slots"]), "revision": 0},
        is_public=False,
        is_archived=False,
        sort_order=0,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_my_schedules(db: AsyncSession, user: User) -> dict:
    schedules = (
        await db.scalars(
            select(Schedule)
            .where(Schedule.owner_id == user.id)
            .order_by(Schedule.sort_order.asc(), Schedule.created_at.desc())
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
    return await _schedule_to_dict(s, include_event_details=s.owner_id == user.id)


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
            logger.warning("删除课表对象失败 key=%s", stored.object_key, exc_info=True)
        await db.delete(stored)
    await db.delete(s)
    await db.commit()


async def get_public_schedule_by_owner(db: AsyncSession, owner_id: uuid.UUID) -> dict:
    """获取某用户的公开课表。仅返回最近一条已公开的课表。"""
    s = (
        await db.scalars(
            select(Schedule)
            .where(
                Schedule.owner_id == owner_id,
                Schedule.is_public.is_(True),
                Schedule.is_archived.is_(False),
            )
            .order_by(Schedule.created_at.desc())
            .limit(1)
        )
    ).first()
    if s is None:
        raise ImageError("NOT_FOUND", "该用户没有公开的课表", 404)
    return await _schedule_to_dict(s, include_event_details=False)


async def get_public_schedule_by_username(db: AsyncSession, username: str) -> dict:
    """按用户名获取公开课表，附带公开的用户信息（供对比使用）。"""
    from app.models.user import User

    u = (await db.scalars(select(User).where(User.username == username).limit(1))).first()
    if u is None:
        raise ImageError("NOT_FOUND", "用户不存在", 404)
    s = (
        await db.scalars(
            select(Schedule)
            .where(
                Schedule.owner_id == u.id,
                Schedule.is_public.is_(True),
                Schedule.is_archived.is_(False),
            )
            .order_by(Schedule.created_at.desc())
            .limit(1)
        )
    ).first()
    if s is None:
        raise ImageError("NOT_FOUND", "该用户没有公开的课表", 404)
    data = await _schedule_to_dict(s, include_event_details=False)
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
    if is_public and s.is_archived:
        raise ImageError("ARCHIVED_SCHEDULE", "已存档的课表不能公开，请先恢复", 422)
    s.is_public = is_public
    await db.commit()
    await db.refresh(s)
    return await _schedule_to_dict(s)


async def update_schedule_meta(
    db: AsyncSession, schedule_id: uuid.UUID, user: User, body: ScheduleMetaRequest
) -> dict:
    """课表架：重命名，或存档/恢复到历史列表；存档同时撤销公开。"""
    s = await db.get(Schedule, schedule_id)
    if s is None or s.owner_id != user.id:
        raise ImageError("NOT_FOUND", "课表不存在", 404)
    if body.original_name is not None:
        s.original_name = body.original_name
    if body.is_archived is not None:
        s.is_archived = body.is_archived
        if body.is_archived:
            s.is_public = False
    await db.commit()
    await db.refresh(s)
    return await _schedule_to_dict(s)


async def reorder_schedules(db: AsyncSession, user: User, body: ScheduleOrderRequest) -> dict:
    """课表架拖动排序：必须提交本人全部课表的完整顺序，避免并发新增导致错位。"""
    schedules = (
        await db.scalars(select(Schedule).where(Schedule.owner_id == user.id))
    ).all()
    owned = {s.id for s in schedules}
    if len(body.ids) != len(set(body.ids)) or set(body.ids) != owned:
        raise ImageError("ORDER_MISMATCH", "课表列表已变化，请刷新后再排序", 409)
    by_id = {s.id: s for s in schedules}
    for position, schedule_id in enumerate(body.ids):
        by_id[schedule_id].sort_order = position
    await db.commit()
    return await get_my_schedules(db, user)


async def create_manual_schedule(db: AsyncSession, user: User, body: ScheduleCreateRequest) -> dict:
    slots = [slot.model_dump() for slot in body.slots]
    timing = (
        body.timing.model_dump(mode="json")
        if body.timing is not None
        else _timing_for_slots(slots)
    )
    _validate_slots_fit_timing(slots, timing)
    schedule = Schedule(
        owner_id=user.id,
        original_name=body.name,
        format="manual",
        parsed_json={
            "slots": slots,
            "revision": 0,
            "timing": timing,
        },
        is_public=False,
        is_archived=False,
        sort_order=0,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return await _schedule_to_dict(schedule)


async def update_schedule_slots(
    db: AsyncSession, schedule_id: uuid.UUID, user: User, body: ScheduleSlotsRequest
) -> dict:
    # 同一课表串行校验版本，防止两个标签页的整表保存互相覆盖。
    schedule = await db.scalar(
        select(Schedule)
        .where(Schedule.id == schedule_id, Schedule.owner_id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if schedule is None:
        raise ImageError("NOT_FOUND", "课表不存在", 404)
    data = schedule.parsed_json or {}
    if body.revision != data.get("revision", 0):
        raise ImageError("SCHEDULE_CONFLICT", "课表已在其他页面更新，请重新加载后再编辑", 409)
    _validate_slots_fit_timing(
        [slot.model_dump() for slot in body.slots],
        normalize_timing(data.get("timing")),
    )
    schedule.parsed_json = {
        **data,
        "slots": [slot.model_dump() for slot in body.slots],
        "revision": body.revision + 1,
    }
    await db.commit()
    await db.refresh(schedule)
    return await _schedule_to_dict(schedule)


async def update_schedule_timing(
    db: AsyncSession, schedule_id: uuid.UUID, user: User, body: ScheduleTimingRequest
) -> dict:
    schedule = await db.scalar(
        select(Schedule)
        .where(Schedule.id == schedule_id, Schedule.owner_id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if schedule is None:
        raise ImageError("NOT_FOUND", "课表不存在", 404)
    data = schedule.parsed_json or {}
    if body.revision != data.get("revision", 0):
        raise ImageError("SCHEDULE_CONFLICT", "课表已在其他页面更新，请重新加载后再编辑", 409)
    _validate_slots_fit_timing(
        list(data.get("slots", [])),
        body.timing.model_dump(mode="json"),
    )
    data = {
        **data,
        "timing": body.timing.model_dump(mode="json"),
        "revision": body.revision + 1,
    }
    schedule.parsed_json = data
    await db.commit()
    await db.refresh(schedule)
    return await _schedule_to_dict(schedule)


async def _schedule_to_dict(s: Schedule, *, include_event_details: bool = True) -> dict:
    slots = []
    for raw in (s.parsed_json or {}).get("slots", []):
        slot = {**raw, "kind": raw.get("kind", "course")}
        if slot["kind"] == "event" and not include_event_details:
            slot = {
                "name": "已有安排",
                "location": "",
                "campus": None,
                "kind": "event",
                "weekday": slot["weekday"],
                "lesson_start": slot["lesson_start"],
                "lesson_end": slot["lesson_end"],
                "weeks": slot["weeks"],
            }
        slots.append(slot)
    return {
        "id": str(s.id),
        "original_name": s.original_name,
        "format": s.format,
        "slots": slots,
        "timing": normalize_timing((s.parsed_json or {}).get("timing")),
        "revision": (s.parsed_json or {}).get("revision", 0),
        "is_public": s.is_public,
        "is_archived": bool(s.is_archived),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
    }
