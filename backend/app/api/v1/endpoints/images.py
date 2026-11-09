"""公开 Gallery 图片端点。"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.response import ok

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/")
async def list_images(request: Request):
    return ok({"items": [], "pagination": {"page": 1, "page_size": 20, "total": 0}})


@router.get("/{image_id}")
async def get_image(image_id: str, request: Request):
    return ok({"id": image_id})


@router.post("/upload-intent")
async def upload_intent(request: Request):
    return ok({"message": "upload-intent stub"})


@router.post("/upload-complete")
async def upload_complete(request: Request):
    return ok({"message": "upload-complete stub"})


@router.delete("/{image_id}")
async def delete_image(image_id: str, request: Request):
    return ok({"message": "delete stub"})


@router.post("/{image_id}/report")
async def report_image(image_id: str, request: Request):
    return ok({"message": "report stub"})


@router.get("/{image_id}/download")
async def download_image(image_id: str, request: Request):
    return ok({"message": "download stub"})