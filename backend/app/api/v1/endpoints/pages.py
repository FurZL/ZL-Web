"""动态页面端点。"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.response import ok

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("/{slug}")
async def get_page(slug: str, request: Request):
    # 仅返回 status=published 的页面
    return ok({"slug": slug, "status": "published", "blocks": []})


@router.get("/admin")
async def list_pages(request: Request):
    return ok({"items": []})


@router.post("/admin")
async def create_page(request: Request):
    return ok({"message": "create stub"})


@router.put("/admin/{page_id}")
async def update_page(page_id: str, request: Request):
    return ok({"message": "update stub"})


@router.post("/admin/{page_id}/publish")
async def publish_page(page_id: str, request: Request):
    return ok({"message": "publish stub"})


@router.post("/admin/{page_id}/unpublish")
async def unpublish_page(page_id: str, request: Request):
    return ok({"message": "unpublish stub"})


@router.delete("/admin/{page_id}")
async def delete_page(page_id: str, request: Request):
    return ok({"message": "delete stub"})