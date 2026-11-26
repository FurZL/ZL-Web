"""图片管理端点：列表、审核、删除、标签编辑、统计。"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
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
from app.services.audit import audit_admin_mutation
from app.services import reports
from app.models.report import Report
from app.models.image import Image, ProfileImage, StoredObject
from app.models.image_job import ImageProcessingJob
from app.services.image import _image_to_dict

router = APIRouter(
    prefix="/admin/images",
    tags=["admin"],
    dependencies=[Depends(require_permission_dep("gallery.image.delete.any")), Depends(audit_admin_mutation)],
)


class ModerationRequest(BaseModel):
    moderation_status: str = Field(pattern="^(pending|approved|rejected)$")


class VisibilityRequest(BaseModel):
    is_public: bool


class TagsRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)


class ReportResolution(BaseModel):
    outcome: Literal["handled", "dismissed", "hide"]


@router.get("/processing-jobs", dependencies=[Depends(require_permission_dep("site_config.manage"))])
async def list_processing_jobs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
    status: Literal["pending", "processing", "failed", "done"] | None = None,
    db: AsyncSession = Depends(get_db),
):
    conditions = [ImageProcessingJob.status == status] if status else []
    total = await db.scalar(select(func.count()).select_from(ImageProcessingJob).where(*conditions)) or 0
    jobs = (await db.scalars(select(ImageProcessingJob).where(*conditions).order_by(
        ImageProcessingJob.created_at.desc(), ImageProcessingJob.id.desc()
    ).offset((page - 1) * page_size).limit(page_size))).all()
    return ok({"items": [{"id": str(job.id), "kind": job.kind, "image_id": str(job.image_id),
        "status": job.status, "attempts": job.attempts, "next_attempt_at": job.next_attempt_at.isoformat(),
        "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat()} for job in jobs],
        "pagination": {"page": page, "page_size": page_size, "total": total}})


@router.post("/processing-jobs/{job_id}/retry", dependencies=[Depends(require_permission_dep("site_config.manage"))])
async def retry_processing_job(job_id: str, db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone

    job = await db.scalar(select(ImageProcessingJob).where(ImageProcessingJob.id == parse_uuid(job_id)).with_for_update())
    if job is None:
        raise error_to_http(ImageError("JOB_NOT_FOUND", "任务不存在", 404))
    if job.status != "failed":
        raise error_to_http(ImageError("JOB_NOT_FAILED", "只能重试失败的任务", 409))
    image = await db.get(Image if job.kind == "gallery" else ProfileImage, job.image_id)
    stored = await db.get(StoredObject, image.stored_object_id) if image else None
    if stored is None or stored.deleted_at is not None:
        raise error_to_http(ImageError("NOT_FOUND", "图片不存在", 404))
    job.status, job.attempts, job.lease_token, job.lease_until = "pending", 0, None, None
    job.next_attempt_at = datetime.now(timezone.utc)
    stored.processing_status = "pending"
    await db.commit()
    return ok({"id": str(job.id), "status": job.status})


@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
    status: Literal["open", "handled", "dismissed"] | None = None,
    db: AsyncSession = Depends(get_db),
):
    return ok(await reports.list_image_reports(db, status=status, page=page, page_size=page_size))


@router.patch("/reports/{report_id}")
async def resolve_report(
    report_id: str, body: ReportResolution,
    user: User = Depends(require_permission_dep("gallery.image.delete.any")),
    db: AsyncSession = Depends(get_db),
):
    try:
        report = await reports.resolve_image_report(db, parse_uuid(report_id), actor_id=user.id, outcome=body.outcome)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"id": str(report.id), "status": report.status, "handled_at": report.handled_at.isoformat()})


@router.get("/reports/{report_id}/image")
async def report_image(report_id: str, db: AsyncSession = Depends(get_db)):
    report = await db.get(Report, parse_uuid(report_id))
    if report is None or report.target_type != "image":
        raise error_to_http(ImageError("REPORT_NOT_FOUND", "举报不存在", 404))
    image = await db.get(Image, parse_uuid(report.target_id))
    if image is None:
        raise error_to_http(ImageError("NOT_FOUND", "图片不存在", 404))
    return ok(await _image_to_dict(db, image))


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
