"""站点公开信息端点（页脚、法律、公开配置）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.response import ok
from app.core.database import get_db
from app.services import site_setting

router = APIRouter(prefix="/site", tags=["site"])


@router.get("/public-config")
async def public_config(db: AsyncSession = Depends(get_db)):
    return ok(await site_setting.get_public_config(db))


@router.get("/footer")
async def footer(db: AsyncSession = Depends(get_db)):
    return ok(await site_setting.get_footer_config(db))


@router.get("/legal")
async def legal(db: AsyncSession = Depends(get_db)):
    return ok(await site_setting.get_legal_config(db))
