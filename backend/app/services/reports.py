"""Administrative handling of image reports."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import Image
from app.models.report import Report


async def list_image_reports(db: AsyncSession, *, status: str | None, page: int, page_size: int) -> dict:
    conditions = [Report.target_type == "image"]
    if status:
        conditions.append(Report.status == status)
    total = await db.scalar(select(func.count()).select_from(Report).where(*conditions)) or 0
    reports = (await db.scalars(select(Report).where(*conditions).order_by(
        Report.created_at.desc(), Report.id.desc()
    ).offset((page - 1) * page_size).limit(page_size))).all()
    image_ids = []
    for report in reports:
        try:
            image_ids.append(uuid.UUID(report.target_id))
        except ValueError:
            pass
    images = {str(image.id): image for image in (await db.scalars(select(Image).where(Image.id.in_(image_ids)))).all()}
    return {"items": [{
        "id": str(report.id), "image_id": report.target_id,
        "image_name": images[report.target_id].original_name if report.target_id in images else None,
        "image_exists": report.target_id in images,
        "image_status": images[report.target_id].moderation_status if report.target_id in images else None,
        "reason": report.reason, "description": report.description,
        "status": report.status, "created_at": report.created_at.isoformat(),
        "handled_at": report.handled_at.isoformat() if report.handled_at else None,
        "handled_by": str(report.handled_by) if report.handled_by else None,
    } for report in reports], "pagination": {"page": page, "page_size": page_size, "total": total}}


async def resolve_image_report(db: AsyncSession, report_id: uuid.UUID, *, actor_id: uuid.UUID, outcome: str) -> Report:
    from app.services.image import ImageError

    report = await db.scalar(select(Report).where(Report.id == report_id, Report.target_type == "image").with_for_update())
    if report is None:
        raise ImageError("REPORT_NOT_FOUND", "举报不存在", 404)
    if report.status != "open":
        raise ImageError("REPORT_ALREADY_HANDLED", "举报已处理，请刷新列表", 409)
    if outcome == "hide":
        try:
            image_id = uuid.UUID(report.target_id)
        except ValueError:
            raise ImageError("NOT_FOUND", "图片不存在，请选择其他处理方式", 404)
        image = await db.scalar(select(Image).where(Image.id == image_id).with_for_update())
        if image is None:
            raise ImageError("NOT_FOUND", "图片不存在，请选择其他处理方式", 404)
        image.moderation_status = "rejected"
        image.is_public = False
    report.status = "dismissed" if outcome == "dismissed" else "handled"
    report.handled_by = actor_id
    report.handled_at = datetime.now(timezone.utc)
    await db.commit()
    return report
