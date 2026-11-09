"""站点公开信息端点（页脚、法律、公开配置）。"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.response import ok

router = APIRouter(prefix="/site", tags=["site"])


@router.get("/public-config")
async def public_config(request: Request):
    return ok({})


@router.get("/footer")
async def footer(request: Request):
    return ok({})


@router.get("/legal")
async def legal(request: Request):
    return ok({})