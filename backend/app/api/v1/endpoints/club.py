"""社团介绍端点。"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.response import ok

router = APIRouter(prefix="/club", tags=["club"])


@router.get("/intro")
async def get_intro(request: Request):
    return ok({"content": ""})


@router.put("/intro")
async def update_intro(request: Request):
    return ok({"message": "update stub"})