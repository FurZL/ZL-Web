"""公告端点：公开列表 + 管理 CRUD。"""

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
from app.services import announcement as announcement_service

router = APIRouter(prefix="/announcements", tags=["announcements"])


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str
    is_pinned: bool = False
    publish_now: bool = False
    expires_at: datetime | None = None


class AnnouncementPatch(BaseModel):
    title: str | None = None
    content: str | None = None
    is_pinned: bool | None = None
    publish_now: bool | None = None
    expires_at: datetime | None = None


def _parse_uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "无效的 ID"})


# ---------- 公开 ----------

@router.get("/published")
async def list_published(db: AsyncSession = Depends(get_db)):
    """公开：已发布且未过期的公告，置顶在前。"""
    return ok(await announcement_service.list_published(db))


# ---------- 管理（需 announcement.manage 权限） ----------

@router.get("/admin")
async def list_admin(
    user: User = Depends(require_permission_dep("site_config.manage")),
    db: AsyncSession = Depends(get_db),
):
    return ok(await announcement_service.list_all(db))


@router.post("/admin")
async def create_announcement(
    body: AnnouncementCreate,
    user: User = Depends(require_permission_dep("site_config.manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await announcement_service.create(
        db,
        title=body.title,
        content=body.content,
        is_pinned=body.is_pinned,
        publish_now=body.publish_now,
        expires_at=body.expires_at,
        user=user,
    )
    return ok(result)


@router.patch("/admin/{announcement_id}")
async def update_announcement(
    announcement_id: str,
    body: AnnouncementPatch,
    user: User = Depends(require_permission_dep("site_config.manage")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await announcement_service.update(
            db, _parse_uuid(announcement_id), **body.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)})
    return ok(result)


@router.delete("/admin/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    user: User = Depends(require_permission_dep("site_config.manage")),
    db: AsyncSession = Depends(get_db),
):
    try:
        await announcement_service.delete(db, _parse_uuid(announcement_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)})
    return ok({"message": "已删除"})
