"""Schedule feature switches, shared by public clients and enforcement."""

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.site_setting import get_setting


class ScheduleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_import_enabled: StrictBool = True
    group_join_enabled: StrictBool = True
    public_share_enabled: StrictBool = True
    fixed_invite_enabled: StrictBool = True


class ScheduleConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_import_enabled: StrictBool
    group_join_enabled: StrictBool
    public_share_enabled: StrictBool
    fixed_invite_enabled: StrictBool


async def get_schedule_config(db: AsyncSession) -> ScheduleConfig:
    value = await get_setting(db, "schedule_config")
    return ScheduleConfig.model_validate(value or {})


async def require_schedule_feature(db: AsyncSession, feature: str) -> None:
    config = await get_schedule_config(db)
    if not getattr(config, feature):
        raise HTTPException(
            status_code=403,
            detail={"code": "SCHEDULE_FEATURE_DISABLED", "message": "该课表功能暂不可用"},
        )
