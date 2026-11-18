"""公告服务：列表、创建、更新、置顶、发布、删除。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Announcement
from app.models.user import User


def _to_dict(a: Announcement) -> dict:
    return {
        "id": str(a.id),
        "title": a.title,
        "content": a.content,
        "status": a.status,
        "is_pinned": a.is_pinned,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


async def list_published(db: AsyncSession) -> dict:
    """公开接口：仅返回已发布且未过期的公告，置顶在前。"""
    now = datetime.now(timezone.utc)
    rows = (
        await db.scalars(
            select(Announcement)
            .where(
                Announcement.status == "published",
                (Announcement.expires_at.is_(None)) | (Announcement.expires_at > now),
            )
            .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
        )
    ).all()
    return {"items": [_to_dict(a) for a in rows]}


async def list_all(db: AsyncSession) -> dict:
    """管理接口：返回全部公告（含草稿/过期）。"""
    rows = (
        await db.scalars(
            select(Announcement).order_by(
                Announcement.is_pinned.desc(), Announcement.created_at.desc()
            )
        )
    ).all()
    return {"items": [_to_dict(a) for a in rows]}


async def get_one(db: AsyncSession, announcement_id: uuid.UUID) -> dict:
    a = await db.get(Announcement, announcement_id)
    if a is None:
        raise ValueError("公告不存在")
    return _to_dict(a)


async def create(
    db: AsyncSession,
    *,
    title: str,
    content: str,
    is_pinned: bool = False,
    publish_now: bool = False,
    expires_at: datetime | None = None,
    user: User | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    a = Announcement(
        title=title,
        content=content,
        status="published" if publish_now else "draft",
        is_pinned=is_pinned,
        published_at=now if publish_now else None,
        expires_at=expires_at,
        created_by=user.id if user else None,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return _to_dict(a)


async def update(
    db: AsyncSession,
    announcement_id: uuid.UUID,
    *,
    title: str | None = None,
    content: str | None = None,
    is_pinned: bool | None = None,
    publish_now: bool | None = None,
    expires_at: datetime | None = None,
) -> dict:
    a = await db.get(Announcement, announcement_id)
    if a is None:
        raise ValueError("公告不存在")
    if title is not None:
        a.title = title
    if content is not None:
        a.content = content
    if is_pinned is not None:
        a.is_pinned = is_pinned
    if publish_now is not None:
        if publish_now and a.status != "published":
            a.status = "published"
            a.published_at = datetime.now(timezone.utc)
        elif not publish_now and a.status == "published":
            a.status = "draft"
    if expires_at is not None:
        a.expires_at = expires_at
    await db.commit()
    await db.refresh(a)
    return _to_dict(a)


async def delete(db: AsyncSession, announcement_id: uuid.UUID) -> None:
    a = await db.get(Announcement, announcement_id)
    if a is None:
        raise ValueError("公告不存在")
    await db.delete(a)
    await db.commit()
