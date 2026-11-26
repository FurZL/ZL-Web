"""课表对比群组：创建、邀请码加入、审批、共享课表、逐人忙闲统计。

群组只对成员可见；成员选择一份自己的课表共享给群，群页面以“我”为基准
逐个成员展示共同空闲/共同忙碌等统计。多人邀约另见 schedule_group_meeting。
"""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.models.schedule_group import ScheduleGroup, ScheduleGroupMember
from app.models.user import User
from app.schemas.schedule import (
    ScheduleGroupCreateRequest,
    ScheduleGroupUpdateRequest,
)
from app.services.image import ImageError
from app.services.schedule import CourseSlot, compare
from app.services.schedule_service import _schedule_to_dict

MAX_GROUPS_PER_USER = 20
MAX_GROUP_MEMBERS = 50
GROUP_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DEFAULT_LESSON_COUNT = 12
MAX_LESSON = 24


def _new_code() -> str:
    return "".join(secrets.choice(GROUP_CODE_ALPHABET) for _ in range(8))


async def _unique_code(db: AsyncSession) -> str:
    for _ in range(20):
        code = _new_code()
        exists = await db.scalar(select(ScheduleGroup.id).where(ScheduleGroup.code == code))
        if not exists:
            return code
    raise ImageError("GROUP_CODE_FAILED", "邀请码生成失败，请重试", 503)


def _group_not_found() -> ImageError:
    return ImageError("GROUP_NOT_FOUND", "群组不存在或你不在群里", 404)


async def _group(db: AsyncSession, group_id: uuid.UUID) -> ScheduleGroup:
    group = await db.get(ScheduleGroup, group_id)
    if group is None:
        raise _group_not_found()
    return group


async def _membership(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> ScheduleGroupMember | None:
    return await db.scalar(
        select(ScheduleGroupMember).where(
            ScheduleGroupMember.group_id == group_id,
            ScheduleGroupMember.user_id == user_id,
        )
    )


async def _active_member(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> ScheduleGroupMember:
    membership = await _membership(db, group_id, user_id)
    if membership is None:
        raise _group_not_found()
    if membership.status != "active":
        raise ImageError("GROUP_NOT_ACTIVE", "你的入群申请还在等待群主同意", 403)
    return membership


async def _active_count(db: AsyncSession, group_id: uuid.UUID) -> int:
    return int(
        await db.scalar(
            select(func.count(ScheduleGroupMember.id)).where(
                ScheduleGroupMember.group_id == group_id,
                ScheduleGroupMember.status == "active",
            )
        )
        or 0
    )


def _week_visible(slot: dict, week: int | None) -> bool:
    weeks = slot.get("weeks") or []
    return week is None or not weeks or week in weeks


def _busy_cells(slots: list[dict], week: int | None) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for slot in slots:
        if not _week_visible(slot, week):
            continue
        for lesson in range(int(slot["lesson_start"]), int(slot["lesson_end"]) + 1):
            cells.add((int(slot["weekday"]), lesson))
    return cells


def _course_slots(slots: list[dict]) -> list[CourseSlot]:
    return [
        CourseSlot(
            name=slot.get("name", ""),
            location=slot.get("location", "") or "",
            weekday=int(slot.get("weekday", 0)),
            lesson_start=int(slot.get("lesson_start", 1)),
            lesson_end=int(slot.get("lesson_end", 1)),
            weeks=list(slot.get("weeks") or []),
            campus=slot.get("campus"),
            kind=slot.get("kind", "course"),
        )
        for slot in slots
    ]


def _busy_stats(my_slots: list[dict], their_slots: list[dict], week: int | None) -> dict:
    """以 7×节次为格子，统计双方共同空闲/共同忙碌/单方忙碌。"""
    my_busy = _busy_cells(my_slots, week)
    their_busy = _busy_cells(their_slots, week)
    lesson_count = min(
        MAX_LESSON,
        max(
            DEFAULT_LESSON_COUNT,
            max((int(slot["lesson_end"]) for slot in [*my_slots, *their_slots]), default=0),
        ),
    )
    total = 7 * lesson_count
    return {
        "lesson_count": lesson_count,
        "both_free": total - len(my_busy | their_busy),
        "both_busy": len(my_busy & their_busy),
        "my_busy_only": len(my_busy - their_busy),
        "their_busy_only": len(their_busy - my_busy),
        "same_classroom": len(
            compare(_course_slots(my_slots), _course_slots(their_slots), week)["same_classroom"]
        ),
    }


async def _group_summary(
    db: AsyncSession, group: ScheduleGroup, membership: ScheduleGroupMember
) -> dict:
    active_count = await _active_count(db, group.id)
    pending_count = int(
        await db.scalar(
            select(func.count(ScheduleGroupMember.id)).where(
                ScheduleGroupMember.group_id == group.id,
                ScheduleGroupMember.status == "pending",
            )
        )
        or 0
    )
    active = membership.status == "active"
    return {
        "id": str(group.id),
        "name": group.name,
        "code": group.code if active else None,
        "owner_id": str(group.owner_id),
        "join_mode": group.join_mode,
        "member_count": active_count,
        "pending_count": pending_count if group.owner_id == membership.user_id else 0,
        "my": {
            "role": membership.role,
            "status": membership.status,
            "schedule_id": str(membership.schedule_id) if membership.schedule_id else None,
            "can_manage": group.owner_id == membership.user_id,
        },
    }


async def list_groups(db: AsyncSession, user: User) -> dict:
    memberships = (
        await db.scalars(
            select(ScheduleGroupMember)
            .where(ScheduleGroupMember.user_id == user.id)
            .order_by(ScheduleGroupMember.created_at.desc())
        )
    ).all()
    items: list[dict] = []
    for membership in memberships:
        group = await db.get(ScheduleGroup, membership.group_id)
        if group is not None:
            items.append(await _group_summary(db, group, membership))
    return {"items": items}


async def create_group(db: AsyncSession, user: User, body: ScheduleGroupCreateRequest) -> dict:
    active_groups = int(
        await db.scalar(
            select(func.count(ScheduleGroupMember.id)).where(
                ScheduleGroupMember.user_id == user.id,
                ScheduleGroupMember.status == "active",
            )
        )
        or 0
    )
    if active_groups >= MAX_GROUPS_PER_USER:
        raise ImageError("GROUP_LIMIT", f"最多同时加入 {MAX_GROUPS_PER_USER} 个群组", 409)
    group = ScheduleGroup(
        name=body.name,
        code=await _unique_code(db),
        owner_id=user.id,
        join_mode=body.join_mode,
    )
    db.add(group)
    await db.flush()
    db.add(
        ScheduleGroupMember(
            group_id=group.id,
            user_id=user.id,
            role="owner",
            status="active",
        )
    )
    await db.commit()
    await db.refresh(group)
    membership = await _membership(db, group.id, user.id)
    return await _group_summary(db, group, membership)


async def join_group(db: AsyncSession, user: User, code: str) -> dict:
    normalized = code.strip().upper()
    group = await db.scalar(select(ScheduleGroup).where(ScheduleGroup.code == normalized))
    if group is None:
        raise ImageError("GROUP_INVITE_INVALID", "邀请码无效", 404)
    existing = await _membership(db, group.id, user.id)
    if existing is not None:
        if existing.status == "active":
            raise ImageError("GROUP_ALREADY_MEMBER", "你已经在这个群里", 409)
        raise ImageError("GROUP_PENDING", "入群申请还在等待群主同意", 409)
    if await _active_count(db, group.id) >= MAX_GROUP_MEMBERS:
        raise ImageError("GROUP_FULL", f"群组最多 {MAX_GROUP_MEMBERS} 人", 409)
    membership = ScheduleGroupMember(
        group_id=group.id,
        user_id=user.id,
        role="member",
        status="active" if group.join_mode == "open" else "pending",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return await _group_summary(db, group, membership)


async def update_group(
    db: AsyncSession, user: User, group_id: uuid.UUID, body: ScheduleGroupUpdateRequest
) -> dict:
    group = await _group(db, group_id)
    if group.owner_id != user.id:
        raise ImageError("GROUP_FORBIDDEN", "只有群主可以修改群组", 403)
    if body.name is not None:
        group.name = body.name
    if body.join_mode is not None:
        group.join_mode = body.join_mode
    await db.commit()
    await db.refresh(group)
    membership = await _membership(db, group.id, user.id)
    return await _group_summary(db, group, membership)


async def delete_group(db: AsyncSession, user: User, group_id: uuid.UUID) -> None:
    group = await _group(db, group_id)
    if group.owner_id != user.id:
        raise ImageError("GROUP_FORBIDDEN", "只有群主可以解散群组", 403)
    members = (
        await db.scalars(
            select(ScheduleGroupMember).where(ScheduleGroupMember.group_id == group_id)
        )
    ).all()
    for member in members:
        await db.delete(member)
    await db.delete(group)
    await db.commit()


async def set_group_schedule(
    db: AsyncSession, user: User, group_id: uuid.UUID, schedule_id: uuid.UUID | None
) -> dict:
    membership = await _active_member(db, group_id, user.id)
    if schedule_id is None:
        membership.schedule_id = None
    else:
        schedule = await db.get(Schedule, schedule_id)
        if (
            schedule is None
            or schedule.owner_id != user.id
            or bool(schedule.is_archived)
        ):
            raise ImageError("GROUP_SCHEDULE_INVALID", "只能选择自己未存档的课表", 422)
        membership.schedule_id = schedule.id
    await db.commit()
    group = await _group(db, group_id)
    return await _group_summary(db, group, membership)


async def approve_member(
    db: AsyncSession, user: User, group_id: uuid.UUID, member_user_id: uuid.UUID
) -> dict:
    group = await _group(db, group_id)
    if group.owner_id != user.id:
        raise ImageError("GROUP_FORBIDDEN", "只有群主可以审批", 403)
    membership = await _membership(db, group_id, member_user_id)
    if membership is None or membership.status != "pending":
        raise ImageError("GROUP_PENDING_NOT_FOUND", "没有待审批的申请", 404)
    if await _active_count(db, group_id) >= MAX_GROUP_MEMBERS:
        raise ImageError("GROUP_FULL", f"群组最多 {MAX_GROUP_MEMBERS} 人", 409)
    membership.status = "active"
    await db.commit()
    owner = await _membership(db, group_id, user.id)
    return await _group_summary(db, group, owner)


async def reject_member(
    db: AsyncSession, user: User, group_id: uuid.UUID, member_user_id: uuid.UUID
) -> None:
    group = await _group(db, group_id)
    if group.owner_id != user.id:
        raise ImageError("GROUP_FORBIDDEN", "只有群主可以拒绝申请", 403)
    membership = await _membership(db, group_id, member_user_id)
    if membership is None or membership.status != "pending":
        raise ImageError("GROUP_PENDING_NOT_FOUND", "没有待审批的申请", 404)
    await db.delete(membership)
    await db.commit()


async def remove_member(
    db: AsyncSession, user: User, group_id: uuid.UUID, member_user_id: uuid.UUID
) -> None:
    group = await _group(db, group_id)
    actor = await _membership(db, group_id, user.id)
    if actor is None or actor.status != "active":
        raise _group_not_found()
    target = await _membership(db, group_id, member_user_id)
    if target is None:
        raise ImageError("GROUP_MEMBER_NOT_FOUND", "成员不存在", 404)
    if target.user_id == group.owner_id:
        raise ImageError("GROUP_OWNER_CANNOT_LEAVE", "群主不能退出，请先解散群组或移交", 409)
    if actor.user_id != group.owner_id and actor.user_id != target.user_id:
        raise ImageError("GROUP_FORBIDDEN", "只有群主可以移除成员", 403)
    await db.delete(target)
    await db.commit()


async def group_detail(
    db: AsyncSession, user: User, group_id: uuid.UUID, week: int | None
) -> dict:
    group = await _group(db, group_id)
    membership = await _membership(db, group_id, user.id)
    if membership is None:
        raise _group_not_found()
    active = membership.status == "active"
    is_owner = group.owner_id == user.id
    active_count = await _active_count(db, group_id)

    base = {
        "id": str(group.id),
        "name": group.name,
        "code": group.code if active else None,
        "owner_id": str(group.owner_id),
        "join_mode": group.join_mode,
        "member_count": active_count,
        "week": week,
        "my": {
            "role": membership.role,
            "status": membership.status,
            "schedule_id": str(membership.schedule_id) if membership.schedule_id else None,
            "can_manage": is_owner,
        },
    }
    if not active:
        base.update({"members": [], "pending": [], "pending_count": 0})
        return base

    memberships = (
        await db.scalars(
            select(ScheduleGroupMember).where(
                ScheduleGroupMember.group_id == group_id,
                ScheduleGroupMember.status == "active",
            )
        )
    ).all()
    user_ids = [m.user_id for m in memberships]
    users = (
        await db.scalars(select(User).where(User.id.in_(user_ids)))
    ).all() if user_ids else []
    user_by_id = {u.id: u for u in users}

    schedule_ids = [m.schedule_id for m in memberships if m.schedule_id]
    schedules = (
        await db.scalars(
            select(Schedule).where(
                Schedule.id.in_(schedule_ids),
                Schedule.is_archived.is_(False),
            )
        )
    ).all() if schedule_ids else []
    schedule_by_id = {s.id: s for s in schedules}

    my_membership = next((m for m in memberships if m.user_id == user.id), membership)
    my_schedule = schedule_by_id.get(my_membership.schedule_id) if my_membership.schedule_id else None
    my_payload = (
        await _schedule_to_dict(my_schedule, include_event_details=True)
        if my_schedule is not None and my_schedule.owner_id == user.id
        else None
    )

    members: list[dict] = []
    for row in memberships:
        member_user = user_by_id.get(row.user_id)
        if member_user is None:
            continue
        is_me = row.user_id == user.id
        schedule = schedule_by_id.get(row.schedule_id) if row.schedule_id else None
        payload = None
        if schedule is not None and schedule.owner_id == row.user_id:
            payload = await _schedule_to_dict(
                schedule, include_event_details=is_me
            )
        stats = None
        if (
            not is_me
            and my_payload is not None
            and payload is not None
            and my_membership.schedule_id
        ):
            stats = _busy_stats(my_payload["slots"], payload["slots"], week)
        members.append(
            {
                "user_id": str(row.user_id),
                "username": member_user.username,
                "display_name": member_user.display_name,
                "role": row.role,
                "is_me": is_me,
                "schedule_id": str(schedule.id) if schedule is not None else None,
                "schedule_name": schedule.original_name if schedule is not None else None,
                "course_count": len(payload["slots"]) if payload is not None else 0,
                "slots": payload["slots"] if payload is not None else [],
                "timing": payload["timing"] if payload is not None else None,
                "stats": stats,
            }
        )
    members.sort(
        key=lambda m: (
            0 if m["is_me"] else 1,
            -(m["stats"]["both_free"] if m["stats"] else -1),
            -(m["stats"]["both_busy"] if m["stats"] else -1),
            m["display_name"],
        )
    )

    pending: list[dict] = []
    if is_owner:
        pending_rows = (
            await db.scalars(
                select(ScheduleGroupMember).where(
                    ScheduleGroupMember.group_id == group_id,
                    ScheduleGroupMember.status == "pending",
                )
            )
        ).all()
        pending_users = (
            await db.scalars(select(User).where(User.id.in_([m.user_id for m in pending_rows])))
        ).all() if pending_rows else []
        user_map = {u.id: u for u in pending_users}
        for row in pending_rows:
            u = user_map.get(row.user_id)
            if u is not None:
                pending.append(
                    {
                        "user_id": str(u.id),
                        "username": u.username,
                        "display_name": u.display_name,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                )

    base.update(
        {
            "members": members,
            "pending": pending,
            "pending_count": len(pending),
        }
    )
    return base
