"""动态页面服务：CRUD、版本快照、发布/下线、版本回滚。

设计：
- schema_json 为白名单 JSON Schema（blocks 列表），前端通过白名单组件渲染。
- 每次保存（create/update/publish）自动生成版本快照。
- 回滚：把指定版本的 schema_snapshot 恢复为当前 schema_json，同时生成新版本。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import DynamicPage, DynamicPageVersion
from app.models.user import User


class PageError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _page_to_dict(p: DynamicPage) -> dict:
    return {
        "id": str(p.id),
        "slug": p.slug,
        "title": p.title,
        "status": p.status,
        "schema_json": p.schema_json,
        "starts_at": p.starts_at.isoformat() if p.starts_at else None,
        "ends_at": p.ends_at.isoformat() if p.ends_at else None,
        "seo_title": p.seo_title,
        "seo_description": p.seo_description,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _version_to_dict(v: DynamicPageVersion) -> dict:
    return {
        "id": str(v.id),
        "page_id": str(v.page_id),
        "version": v.version,
        "schema_snapshot": v.schema_snapshot,
        "change_summary": v.change_summary,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


async def _next_version_number(db: AsyncSession, page_id: uuid.UUID) -> int:
    max_v = await db.scalar(
        select(func.coalesce(func.max(DynamicPageVersion.version), 0)).where(
            DynamicPageVersion.page_id == page_id
        )
    )
    return (max_v or 0) + 1


async def _save_snapshot(
    db: AsyncSession,
    page_id: uuid.UUID,
    schema_json: dict,
    operator_id: uuid.UUID | None,
    change_summary: str | None = None,
) -> dict:
    v = DynamicPageVersion(
        page_id=page_id,
        version=await _next_version_number(db, page_id),
        schema_snapshot=schema_json,
        operator_id=operator_id,
        change_summary=change_summary,
    )
    db.add(v)
    await db.flush()
    return _version_to_dict(v)


# ---------- 公开端点 ----------

async def get_published_page(db: AsyncSession, slug: str) -> dict:
    now = datetime.now(timezone.utc)
    p = (
        await db.scalars(
            select(DynamicPage)
            .where(
                DynamicPage.slug == slug,
                DynamicPage.status == "published",
            )
            .limit(1)
        )
    ).first()
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    # 时间窗口检查（如果设置了 starts_at / ends_at）
    if p.starts_at and now < p.starts_at:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    if p.ends_at and now > p.ends_at:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    return _page_to_dict(p)


# ---------- 管理端点 ----------

async def list_pages(db: AsyncSession) -> dict:
    rows = (await db.scalars(select(DynamicPage).order_by(DynamicPage.updated_at.desc()))).all()
    return {"items": [_page_to_dict(p) for p in rows]}


async def get_page(db: AsyncSession, page_id: uuid.UUID) -> dict:
    p = await db.get(DynamicPage, page_id)
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    return _page_to_dict(p)


async def create_page(
    db: AsyncSession,
    *,
    slug: str,
    title: str,
    schema_json: dict,
    description: str | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    seo_title: str | None = None,
    seo_description: str | None = None,
    user: User | None = None,
) -> dict:
    existing = (
        await db.scalars(select(DynamicPage).where(DynamicPage.slug == slug).limit(1))
    ).first()
    if existing:
        raise PageError("SLUG_EXISTS", "该 slug 已被使用")

    p = DynamicPage(
        slug=slug,
        title=title,
        schema_json=schema_json,
        starts_at=starts_at,
        ends_at=ends_at,
        seo_title=seo_title,
        seo_description=seo_description,
        status="draft",
        created_by=user.id if user else None,
    )
    db.add(p)
    await db.flush()
    await _save_snapshot(db, p.id, schema_json, user.id if user else None, "创建页面")
    await db.commit()
    await db.refresh(p)
    return _page_to_dict(p)


async def update_page(
    db: AsyncSession,
    page_id: uuid.UUID,
    *,
    user: User | None = None,
    change_summary: str | None = None,
    **kwargs,
) -> dict:
    p = await db.get(DynamicPage, page_id)
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)

    new_schema = kwargs.pop("schema_json", None)
    for k, v in kwargs.items():
        if v is not None and hasattr(p, k):
            setattr(p, k, v)

    if new_schema is not None:
        p.schema_json = new_schema
        await _save_snapshot(
            db, page_id, new_schema, user.id if user else None,
            change_summary or "更新页面",
        )

    await db.commit()
    await db.refresh(p)
    return _page_to_dict(p)


async def publish_page(db: AsyncSession, page_id: uuid.UUID, user: User | None = None) -> dict:
    p = await db.get(DynamicPage, page_id)
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    p.status = "published"
    p.published_at = datetime.now(timezone.utc)
    await _save_snapshot(db, page_id, p.schema_json, user.id if user else None, "发布页面")
    await db.commit()
    await db.refresh(p)
    return _page_to_dict(p)


async def unpublish_page(db: AsyncSession, page_id: uuid.UUID, user: User | None = None) -> dict:
    p = await db.get(DynamicPage, page_id)
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    p.status = "draft"
    await db.commit()
    await db.refresh(p)
    return _page_to_dict(p)


async def delete_page(db: AsyncSession, page_id: uuid.UUID) -> None:
    p = await db.get(DynamicPage, page_id)
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    # 删除版本记录
    versions = (
        await db.scalars(
            select(DynamicPageVersion).where(DynamicPageVersion.page_id == page_id)
        )
    ).all()
    for v in versions:
        await db.delete(v)
    await db.delete(p)
    await db.commit()


async def list_versions(db: AsyncSession, page_id: uuid.UUID) -> dict:
    p = await db.get(DynamicPage, page_id)
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    rows = (
        await db.scalars(
            select(DynamicPageVersion)
            .where(DynamicPageVersion.page_id == page_id)
            .order_by(DynamicPageVersion.version.desc())
        )
    ).all()
    return {"items": [_version_to_dict(v) for v in rows]}


async def rollback_page(
    db: AsyncSession,
    page_id: uuid.UUID,
    version_id: uuid.UUID,
    user: User | None = None,
) -> dict:
    p = await db.get(DynamicPage, page_id)
    if p is None:
        raise PageError("NOT_FOUND", "页面不存在", 404)
    v = await db.get(DynamicPageVersion, version_id)
    if v is None or v.page_id != page_id:
        raise PageError("NOT_FOUND", "版本不存在", 404)

    p.schema_json = v.schema_snapshot
    await _save_snapshot(
        db, page_id, v.schema_snapshot, user.id if user else None,
        f"回滚到版本 v{v.version}",
    )
    await db.commit()
    await db.refresh(p)
    return _page_to_dict(p)
