"""Aggregate dashboard counts without exposing user records."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.event import EventRegistration
from app.models.image import Image
from app.models.report import Report
from app.models.user import User

router = APIRouter(prefix="/admin/dashboard", tags=["admin"], dependencies=[Depends(require_permission_dep("site_config.manage"))])


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)):
    counts = (await db.execute(select(
        select(func.count()).select_from(User).scalar_subquery(),
        select(func.count()).select_from(User).where(User.status == "pending").scalar_subquery(),
        select(func.count()).select_from(Image).scalar_subquery(),
        select(func.count()).select_from(EventRegistration).where(EventRegistration.status.in_(["registered", "checked_in"])).scalar_subquery(),
        select(func.count()).select_from(Report).where(Report.target_type == "image", Report.status == "open").scalar_subquery(),
    ))).one()
    return ok(dict(zip(("users", "pending_users", "images", "registrations", "open_reports"), counts)))
