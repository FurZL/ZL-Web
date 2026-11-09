"""动态页面端点：公开读取 + 管理 CRUD + 版本回滚。"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.user import User
from app.services import page as page_service
from app.services.page import PageError

router = APIRouter(prefix="/pages", tags=["pages"])


class PageCreateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9\-]+$")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    page_schema: dict = Field(default_factory=dict)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    seo_title: str | None = None
    seo_description: str | None = None


class PagePatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    page_schema: dict | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    change_summary: str | None = None


def _parse_uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "无效的 ID"})


def _handle_error(exc: PageError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


# ---------- 公开 ----------

@router.get("/{slug}")
async def get_page(slug: str, db: AsyncSession = Depends(get_db)):
    """公开：仅返回已发布且在有效期内的页面。"""
    try:
        result = await page_service.get_published_page(db, slug)
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


# ---------- 管理（需 page.publish 权限） ----------

@router.get("/admin/list")
async def list_pages(
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await page_service.list_pages(db)
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.post("/admin")
async def create_page(
    body: PageCreateRequest,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await page_service.create_page(
            db,
            slug=body.slug,
            title=body.title,
            schema_json=body.page_schema,
            description=body.description,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            seo_title=body.seo_title,
            seo_description=body.seo_description,
            user=user,
        )
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.get("/admin/{page_id}")
async def get_page_detail(
    page_id: str,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await page_service.get_page(db, _parse_uuid(page_id))
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.put("/admin/{page_id}")
async def update_page(
    page_id: str,
    body: PagePatchRequest,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    kwargs = body.model_dump(exclude_unset=True)
    change_summary = kwargs.pop("change_summary", None)
    if "page_schema" in kwargs:
        kwargs["schema_json"] = kwargs.pop("page_schema")
    try:
        result = await page_service.update_page(
            db, _parse_uuid(page_id), user=user, change_summary=change_summary, **kwargs
        )
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.post("/admin/{page_id}/publish")
async def publish_page(
    page_id: str,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await page_service.publish_page(db, _parse_uuid(page_id), user)
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.post("/admin/{page_id}/unpublish")
async def unpublish_page(
    page_id: str,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await page_service.unpublish_page(db, _parse_uuid(page_id), user)
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.delete("/admin/{page_id}")
async def delete_page(
    page_id: str,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        await page_service.delete_page(db, _parse_uuid(page_id))
    except PageError as exc:
        raise _handle_error(exc)
    return ok({"message": "已删除"})


@router.get("/admin/{page_id}/versions")
async def list_versions(
    page_id: str,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await page_service.list_versions(db, _parse_uuid(page_id))
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)


@router.post("/admin/{page_id}/rollback/{version_id}")
async def rollback_page(
    page_id: str,
    version_id: str,
    user: User = Depends(require_permission_dep("page.publish")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await page_service.rollback_page(
            db, _parse_uuid(page_id), _parse_uuid(version_id), user
        )
    except PageError as exc:
        raise _handle_error(exc)
    return ok(result)
