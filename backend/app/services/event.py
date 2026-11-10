"""活动服务：活动 CRUD、报名/候补/取消、签到。

报名规则：
- 活动必须已发布且未取消。
- 报名窗口未到或已过则拒绝。
- 已报名/候补则返回现有记录（幂等）。
- 名额满时自动进入候补名单，有取消时自动递补。
- 报名使用幂等键防止重复提交。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventRegistration
from app.models.user import User


class EventError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _event_to_dict(e: Event, extra: dict | None = None) -> dict:
    d = {
        "id": str(e.id),
        "title": e.title,
        "description": e.description,
        "location": e.location,
        "starts_at": e.starts_at.isoformat() if e.starts_at else None,
        "ends_at": e.ends_at.isoformat() if e.ends_at else None,
        "capacity": e.capacity,
        "registration_starts_at": e.registration_starts_at.isoformat() if e.registration_starts_at else None,
        "registration_ends_at": e.registration_ends_at.isoformat() if e.registration_ends_at else None,
        "status": e.status,
        "created_by": str(e.created_by) if e.created_by else None,
    }
    if extra:
        d.update(extra)
    return d


def _reg_to_dict(r: EventRegistration, user: User | None = None) -> dict:
    d = {
        "id": str(r.id),
        "event_id": str(r.event_id),
        "user_id": str(r.user_id),
        "status": r.status,
        "signup_at": r.signup_at.isoformat() if r.signup_at else None,
        "checkin_at": r.checkin_at.isoformat() if r.checkin_at else None,
    }
    if user:
        d["user"] = {
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
        }
    return d


async def _count_registered(db: AsyncSession, event_id: uuid.UUID) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(EventRegistration)
        .where(
            EventRegistration.event_id == event_id,
            EventRegistration.status.in_(["registered", "checked_in"]),
        )
    )
    return result or 0


async def _count_waitlisted(db: AsyncSession, event_id: uuid.UUID) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(EventRegistration)
        .where(
            EventRegistration.event_id == event_id,
            EventRegistration.status == "waitlisted",
        )
    )
    return result or 0


async def _batch_counts(db: AsyncSession, event_ids: list[uuid.UUID]) -> dict:
    """一次性查询所有活动的报名/候补统计，避免 N+1。

    返回 {event_id: {"registered": int, "waitlist": int}}
    """
    if not event_ids:
        return {}
    rows = await db.execute(
        select(
            EventRegistration.event_id,
            EventRegistration.status,
            func.count().label("cnt"),
        )
        .where(
            EventRegistration.event_id.in_(event_ids),
            EventRegistration.status.in_(["registered", "checked_in", "waitlisted"]),
        )
        .group_by(EventRegistration.event_id, EventRegistration.status)
    )
    counts: dict = {eid: {"registered": 0, "waitlist": 0} for eid in event_ids}
    for event_id, status, cnt in rows:
        key = "registered" if status in ("registered", "checked_in") else "waitlist"
        counts[event_id][key] = int(cnt)
    return counts


async def admin_list_events(db: AsyncSession) -> dict:
    """管理端活动列表：一次查询 + 批量统计，无 N+1。"""
    rows = (
        await db.scalars(select(Event).order_by(Event.starts_at.desc()))
    ).all()
    counts = await _batch_counts(db, [e.id for e in rows])
    items = []
    for e in rows:
        c = counts.get(e.id, {"registered": 0, "waitlist": 0})
        items.append({
            **_event_to_dict(e),
            "registered_count": c["registered"],
            "waitlist_count": c["waitlist"],
        })
    return {"items": items}


async def _promote_waitlist(db: AsyncSession, event_id: uuid.UUID, capacity: int | None):
    """名额有空缺时，把候补名单最早的人递补为正式报名。"""
    if capacity is None:
        return
    registered = await _count_registered(db, event_id)
    while registered < capacity:
        next_w = (
            await db.scalars(
                select(EventRegistration)
                .where(
                    EventRegistration.event_id == event_id,
                    EventRegistration.status == "waitlisted",
                )
                .order_by(EventRegistration.signup_at.asc())
                .limit(1)
            )
        ).first()
        if next_w is None:
            break
        next_w.status = "registered"
        registered += 1


# ---------- 公开 / 成员端点 ----------

async def list_events(db: AsyncSession, user: User | None = None) -> dict:
    """公开活动列表：已发布或已取消（让用户看到），按开始时间排序。"""
    rows = (
        await db.scalars(
            select(Event)
            .where(Event.status.in_(["published", "cancelled"]))
            .order_by(Event.starts_at.desc())
        )
    ).all()
    items = []
    for e in rows:
        registered_count = await _count_registered(db, e.id)
        waitlist_count = await _count_waitlisted(db, e.id)
        my_reg = None
        if user:
            my_reg = (
                await db.scalars(
                    select(EventRegistration)
                    .where(
                        EventRegistration.event_id == e.id,
                        EventRegistration.user_id == user.id,
                        EventRegistration.status.in_(["registered", "waitlisted", "checked_in"]),
                    )
                    .limit(1)
                )
            ).first()
        items.append(
            _event_to_dict(e, {
                "registered_count": registered_count,
                "waitlist_count": waitlist_count,
                "my_status": my_reg.status if my_reg else None,
            })
        )
    return {"items": items}


async def get_event(db: AsyncSession, event_id: uuid.UUID, user: User | None = None) -> dict:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)
    if e.status == "draft":
        raise EventError("NOT_FOUND", "活动不存在", 404)
    registered_count = await _count_registered(db, e.id)
    waitlist_count = await _count_waitlisted(db, e.id)
    my_reg = None
    if user:
        my_reg = (
            await db.scalars(
                select(EventRegistration)
                .where(
                    EventRegistration.event_id == e.id,
                    EventRegistration.user_id == user.id,
                    EventRegistration.status.in_(["registered", "waitlisted", "checked_in"]),
                )
                .limit(1)
            )
        ).first()
    return _event_to_dict(e, {
        "registered_count": registered_count,
        "waitlist_count": waitlist_count,
        "my_registration": _reg_to_dict(my_reg) if my_reg else None,
    })


async def register(
    db: AsyncSession,
    event_id: uuid.UUID,
    user: User,
    idempotency_key: str | None = None,
) -> dict:
    e = await db.get(Event, event_id)
    if e is None or e.status == "draft":
        raise EventError("NOT_FOUND", "活动不存在", 404)
    if e.status == "cancelled":
        raise EventError("EVENT_CANCELLED", "活动已取消")

    now = datetime.now(timezone.utc)
    if e.registration_starts_at and now < e.registration_starts_at:
        raise EventError("NOT_OPEN", "报名尚未开始")
    if e.registration_ends_at and now > e.registration_ends_at:
        raise EventError("CLOSED", "报名已截止")

    # 幂等：同一幂等键已有记录则直接返回
    if idempotency_key:
        existing = (
            await db.scalars(
                select(EventRegistration)
                .where(EventRegistration.idempotency_key == idempotency_key)
                .limit(1)
            )
        ).first()
        if existing:
            return _reg_to_dict(existing)

    # 重复报名检查
    existing = (
        await db.scalars(
            select(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
                EventRegistration.status.in_(["registered", "waitlisted", "checked_in"]),
            )
            .limit(1)
        )
    ).first()
    if existing:
        return _reg_to_dict(existing)

    # 容量检查
    registered = await _count_registered(db, event_id)
    capacity = e.capacity
    status = "registered"
    if capacity is not None and registered >= capacity:
        status = "waitlisted"

    reg = EventRegistration(
        event_id=event_id,
        user_id=user.id,
        status=status,
        idempotency_key=idempotency_key or str(uuid.uuid4()),
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return _reg_to_dict(reg)


async def cancel_registration(
    db: AsyncSession,
    event_id: uuid.UUID,
    user: User,
) -> dict:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)

    reg = (
        await db.scalars(
            select(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
                EventRegistration.status.in_(["registered", "waitlisted", "checked_in"]),
            )
            .limit(1)
        )
    ).first()
    if reg is None:
        raise EventError("NOT_REGISTERED", "尚未报名该活动", 404)

    reg.status = "cancelled"
    await db.commit()

    # 递补候补
    if e.capacity is not None:
        await _promote_waitlist(db, event_id, e.capacity)
        await db.commit()

    return {"message": "已取消报名"}


async def checkin(db: AsyncSession, event_id: uuid.UUID, user: User) -> dict:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)

    reg = (
        await db.scalars(
            select(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
                EventRegistration.status.in_(["registered", "waitlisted"]),
            )
            .limit(1)
        )
    ).first()
    if reg is None:
        raise EventError("NOT_REGISTERED", "尚未报名该活动", 404)
    if reg.status == "waitlisted":
        raise EventError("WAITLISTED", "候补中，尚不能签到")
    if reg.checkin_at is not None:
        return _reg_to_dict(reg)

    reg.status = "checked_in"
    reg.checkin_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reg)
    return _reg_to_dict(reg)


# ---------- 管理端点 ----------

async def create_event(
    db: AsyncSession,
    *,
    title: str,
    description: str | None,
    location: str | None,
    starts_at: datetime,
    ends_at: datetime,
    capacity: int | None,
    registration_starts_at: datetime | None,
    registration_ends_at: datetime | None,
    publish_now: bool = False,
    user: User | None = None,
) -> dict:
    e = Event(
        title=title,
        description=description,
        location=location,
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=capacity,
        registration_starts_at=registration_starts_at,
        registration_ends_at=registration_ends_at,
        status="published" if publish_now else "draft",
        created_by=user.id if user else None,
    )
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return _event_to_dict(e)


async def update_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    **kwargs,
) -> dict:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)
    for k, v in kwargs.items():
        if v is not None and hasattr(e, k):
            setattr(e, k, v)
    await db.commit()
    await db.refresh(e)
    return _event_to_dict(e)


async def set_event_status(db: AsyncSession, event_id: uuid.UUID, status: str) -> dict:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)
    if status not in ("draft", "published", "cancelled"):
        raise EventError("INVALID_STATUS", "无效的活动状态")
    e.status = status
    await db.commit()
    await db.refresh(e)
    return _event_to_dict(e)


async def delete_event(db: AsyncSession, event_id: uuid.UUID) -> None:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)
    # 删除报名记录
    regs = (
        await db.scalars(
            select(EventRegistration).where(EventRegistration.event_id == event_id)
        )
    ).all()
    for r in regs:
        db.delete(r)
    db.delete(e)
    await db.commit()


async def list_registrations(db: AsyncSession, event_id: uuid.UUID) -> dict:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)
    regs = (
        await db.scalars(
            select(EventRegistration)
            .where(EventRegistration.event_id == event_id)
            .order_by(EventRegistration.signup_at.asc())
        )
    ).all()
    items = []
    for r in regs:
        u = await db.get(User, r.user_id)
        items.append(_reg_to_dict(r, u))
    return {
        "event": _event_to_dict(e),
        "items": items,
        "registered_count": await _count_registered(db, event_id),
        "waitlist_count": await _count_waitlisted(db, event_id),
    }


async def admin_checkin(db: AsyncSession, event_id: uuid.UUID, registration_id: uuid.UUID) -> dict:
    e = await db.get(Event, event_id)
    if e is None:
        raise EventError("NOT_FOUND", "活动不存在", 404)
    reg = await db.get(EventRegistration, registration_id)
    if reg is None or reg.event_id != event_id:
        raise EventError("NOT_FOUND", "报名记录不存在", 404)
    if reg.status == "checked_in":
        return _reg_to_dict(reg)
    if reg.status == "cancelled":
        raise EventError("CANCELLED", "该报名已取消")
    reg.status = "checked_in"
    reg.checkin_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reg)
    u = await db.get(User, reg.user_id)
    return _reg_to_dict(reg, u)
