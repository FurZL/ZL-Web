"""管理端：网站设置与 Provider 测试。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_permission_dep
from app.api.response import ok

router = APIRouter(
    prefix="/admin/settings",
    tags=["admin"],
    dependencies=[Depends(require_permission_dep("site_config.manage"))],
)


@router.get("/")
async def list_settings(request: Request):
    return ok({"items": []})


@router.put("/")
async def update_settings(request: Request):
    return ok({"message": "update stub"})


@router.post("/storage/test")
async def test_storage(request: Request):
    return ok({"message": "test stub"})


@router.post("/email/test")
async def test_email(request: Request):
    return ok({"message": "test stub"})


@router.post("/sms/test")
async def test_sms(request: Request):
    return ok({"message": "test stub"})


@router.post("/captcha/test")
async def test_captcha(request: Request):
    return ok({"message": "test stub"})