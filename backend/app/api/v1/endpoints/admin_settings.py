"""管理端：网站设置读写与 Provider 测试。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.user import User
from app.services import site_setting

router = APIRouter(
    prefix="/admin/settings",
    tags=["admin"],
    dependencies=[Depends(require_permission_dep("site_config.manage"))],
)


class SettingUpsert(BaseModel):
    key: str
    value: dict
    category: str | None = None
    is_public: bool = False


@router.get("/")
async def list_settings(db: AsyncSession = Depends(get_db)):
    return ok({"items": await site_setting.list_settings(db)})


@router.put("/")
async def upsert_setting(
    body: SettingUpsert,
    user: User = Depends(require_permission_dep("site_config.manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await site_setting.upsert_setting(
        db,
        key=body.key,
        value=body.value,
        category=body.category,
        is_public=body.is_public,
        updated_by=user.id,
    )
    return ok(result)


# ---------- Provider 测试（仅开发/诊断用） ----------

@router.post("/storage/test")
async def test_storage():
    from app.providers.factory import get_storage_provider

    storage = get_storage_provider()
    configured = getattr(storage, "configured", False)
    return ok({"configured": configured, "provider": type(storage).__name__})


@router.post("/email/test")
async def test_email():
    from app.providers.factory import get_email_provider

    provider = get_email_provider()
    return ok({"provider": type(provider).__name__})


@router.post("/sms/test")
async def test_sms():
    from app.providers.factory import get_sms_provider

    provider = get_sms_provider()
    return ok({"provider": type(provider).__name__})


@router.post("/captcha/test")
async def test_captcha():
    from app.providers.factory import get_captcha_provider

    provider = get_captcha_provider()
    return ok({"provider": type(provider).__name__})
