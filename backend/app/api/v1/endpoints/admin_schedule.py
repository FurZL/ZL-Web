"""Privacy-preserving schedule administration."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.schedule import Schedule
from app.models.schedule_appointment import ScheduleAppointment
from app.models.schedule_group import ScheduleGroup
from app.models.setting import SiteSetting
from app.models.user import User
from app.services.schedule_config import ScheduleConfig, ScheduleConfigUpdate, get_schedule_config
from app.utils import mask_ip

router = APIRouter(prefix="/admin/schedule", tags=["admin"])
admin = require_permission_dep("site_config.manage")


@router.get("/config")
async def read_config(_user: User = Depends(admin), db: AsyncSession = Depends(get_db)):
    return ok((await get_schedule_config(db)).model_dump())


@router.put("/config")
async def update_config(
    body: ScheduleConfigUpdate, request: Request,
    user: User = Depends(admin), db: AsyncSession = Depends(get_db),
):
    # Lock the single settings row so its change and audit record commit together.
    await db.execute(insert(SiteSetting).values(
        key="schedule_config", value_json=ScheduleConfig().model_dump(),
        category="schedule", is_public=False,
    ).on_conflict_do_nothing(index_elements=[SiteSetting.key]))
    row = (await db.scalars(select(SiteSetting).where(
        SiteSetting.key == "schedule_config"
    ).with_for_update())).one()
    previous = ScheduleConfig.model_validate(row.value_json or {}).model_dump()
    updated = body.model_dump()
    if previous != updated:
        row.value_json = updated
        row.updated_by = user.id
        db.add(AuditLog(
            actor_user_id=user.id, action="schedule.config.update",
            target_type="site_setting", target_id="schedule_config",
            request_id=getattr(request.state, "request_id", None),
            ip_masked=mask_ip(request.client.host) if request.client else None,
            metadata_json={"before": previous, "after": updated},
        ))
    await db.commit()
    return ok(updated)


@router.get("/overview")
async def overview(_user: User = Depends(admin), db: AsyncSession = Depends(get_db)):
    counts = (await db.execute(select(
        func.count(Schedule.id),
        func.count(Schedule.id).filter(Schedule.is_archived.is_(True)),
        func.count(Schedule.id).filter(Schedule.is_public.is_(True)),
    ))).one()
    groups = await db.scalar(select(func.count(ScheduleGroup.id)))
    statuses = (await db.execute(select(
        ScheduleAppointment.status, func.count(ScheduleAppointment.id)
    ).group_by(ScheduleAppointment.status))).all()
    return ok({
        "schedules": counts[0], "archived": counts[1], "public": counts[2],
        "groups": groups, "appointments_by_status": dict(statuses),
    })


@router.get("/audit")
async def audit(_user: User = Depends(admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(AuditLog).where(
        AuditLog.action == "schedule.config.update"
    ).order_by(AuditLog.created_at.desc()).limit(50))).all()
    return ok({"items": [{
        "id": str(row.id), "actor_id": str(row.actor_user_id) if row.actor_user_id else None,
        "created_at": row.created_at.isoformat(), "changes": row.metadata_json,
    } for row in rows]})
