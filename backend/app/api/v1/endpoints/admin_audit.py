"""Read-only, administrator-only audit search."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(prefix="/admin/audit", tags=["admin"], dependencies=[Depends(require_permission_dep("site_config.manage"))])


@router.get("")
async def list_audit(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    target_type: str | None = Query(None, max_length=64),
    action: str | None = Query(None, max_length=128),
    actor_id: uuid.UUID | None = None,
    start: datetime | None = None, end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    if (start and start.utcoffset() is None) or (end and end.utcoffset() is None):
        raise HTTPException(status_code=422, detail="时间必须包含时区")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="开始时间不能晚于结束时间")
    filters = []
    if target_type:
        filters.append(AuditLog.target_type == target_type)
    if action:
        filters.append(AuditLog.action == action)
    if actor_id:
        filters.append(AuditLog.actor_user_id == actor_id)
    if start:
        filters.append(AuditLog.created_at >= start)
    if end:
        filters.append(AuditLog.created_at <= end)
    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    rows = (await db.execute(select(AuditLog, User.username).outerjoin(User, User.id == AuditLog.actor_user_id).where(*filters).order_by(
        AuditLog.created_at.desc(), AuditLog.id.desc()
    ).offset((page - 1) * page_size).limit(page_size))).all()
    return ok({"items": [{
        "id": str(row.id), "actor_id": str(row.actor_user_id) if row.actor_user_id else None,
        "actor_name": actor_name, "action": row.action, "target_type": row.target_type, "target_id": row.target_id,
        "request_id": row.request_id, "ip_masked": row.ip_masked,
        "changes": row.metadata_json, "created_at": row.created_at.isoformat(),
    } for row, actor_name in rows], "total": total, "page": page, "page_size": page_size})
