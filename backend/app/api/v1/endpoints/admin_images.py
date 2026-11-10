"""图片管理端点：列表、审核、删除、标签编辑、统计。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
from app.api.response import error_to_http, ok, parse_uuid
from app.core.database import get_db
from app.models.user import User
from app.services.admin_image import (
    delete_image,
    get_stats,
    list_all_images,
    set_moderation,
    set_visibility,
    update_tags,
)
from app.services.image import ImageError

router = APIRouter(
    prefix="/admin/images",
    tags=["admin"],
    dependencies=[Depends(require_permission_dep("gallery.image.delete.any"))],
)


class ModerationRequest(BaseModel):
    moderation_status: str = Field(pattern="^(pending|approved|rejected)$")


class VisibilityRequest(BaseModel):
    is_public: bool


class TagsRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    return ok(await get_stats(db))


@router.get("/")
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status: str | None = Query(None, pattern="^(pending|approved|rejected)$"),
    is_public: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await list_all_images(
            db, page=page, page_size=page_size, status=status, is_public=is_public
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.patch("/{image_id}/moderation")
async def set_image_moderation(
    image_id: str,
    body: ModerationRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await set_moderation(db, parse_uuid(image_id), body.moderation_status)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.patch("/{image_id}/visibility")
async def set_image_visibility(
    image_id: str,
    body: VisibilityRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await set_visibility(db, parse_uuid(image_id), body.is_public)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.put("/{image_id}/tags")
async def set_image_tags(
    image_id: str,
    body: TagsRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await update_tags(db, parse_uuid(image_id), body.tags)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.delete("/{image_id}")
async def remove_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_image(db, parse_uuid(image_id))
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"message": "已删除"})
