"""公开 Gallery 图片端点。

上传走预签名直传：upload-intent 签发 URL → 前端直传 COS → upload-complete 落库。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission_dep
from app.api.response import error_to_http, ok, parse_uuid
from app.core.database import get_db
from app.core.permissions import has_permission
from app.models.image import Image, StoredObject
from app.models.report import Report
from app.models.user import User
from app.providers.factory import get_storage_provider
from app.schemas.image import (
    UploadCompleteRequest,
    UploadIntentRequest,
)
from app.services import image as image_service
from app.services.admin_image import delete_image as admin_delete_image
from app.services.image import ImageError

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/")
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    result = await image_service.list_public_images(db, page=page, page_size=page_size)
    return ok(result)


@router.get("/{image_id}")
async def get_image(image_id: str, db: AsyncSession = Depends(get_db)):
    # 简化：直接查库返回单图
    uid = parse_uuid(image_id, "图片 ID")


    image = await db.get(Image, uid)
    if image is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "图片不存在"})
    return ok(await image_service._image_to_dict(db, image))


@router.post("/upload-intent")
async def upload_intent(
    body: UploadIntentRequest,
    user: User = Depends(require_permission_dep("gallery.image.upload.public")),
):
    try:
        intent = await image_service.create_upload_intent(
            user=user,
            filename=body.filename,
            mime_type=body.mime_type,
            size_bytes=body.size_bytes,
            purpose=body.purpose,
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(intent)


@router.post("/upload-complete")
async def upload_complete(
    body: UploadCompleteRequest,
    user: User = Depends(require_permission_dep("gallery.image.upload.public")),
    db: AsyncSession = Depends(get_db),
):
    try:
        image = await image_service.complete_upload(
            db,
            user=user,
            object_key=body.object_key,
            bucket=body.bucket,
            original_name=body.original_name or body.object_key.rsplit("/", 1)[-1],
            purpose=body.purpose,
            description=body.description,
            tags=body.tags,
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(await image_service._image_to_dict(db, image))


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):


    uid = parse_uuid(image_id, "图片 ID")


    image = await db.get(Image, uid)
    if image is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "图片不存在"})

    # 仅上传者本人或有任意删除权限的角色可删除
    if image.uploader_id != user.id and not has_permission(user.role, "gallery.image.delete.any"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权删除该图片"})



    try:
        await admin_delete_image(db, uid)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"message": "已删除"})


@router.post("/{image_id}/report")
async def report_image(
    image_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):


    uid = parse_uuid(image_id, "图片 ID")


    image = await db.get(Image, uid)
    if image is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "图片不存在"})

    # 不能举报自己的图片
    if image.uploader_id == user.id:
        raise HTTPException(status_code=400, detail={"code": "SELF_REPORT", "message": "不能举报自己的图片"})

    # 同一用户对同一图片只能有一条未处理的举报


    existing = (
        await db.scalars(
            select(Report)
            .where(
                Report.reporter_id == user.id,
                Report.target_type == "image",
                Report.target_id == str(uid),
                Report.status == "open",
            )
            .limit(1)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "ALREADY_REPORTED", "message": "已提交过举报，请等待处理"})

    report = Report(
        reporter_id=user.id,
        target_type="image",
        target_id=str(uid),
        reason="inappropriate",
        status="open",
    )
    db.add(report)
    await db.commit()
    return ok({"message": "举报已提交，管理员会尽快处理"})


@router.get("/{image_id}/download")
async def download_image(
    image_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 私有/公开原图下载：签发短时效签名 URL
    uid = parse_uuid(image_id, "图片 ID")



    image = await db.get(Image, uid)
    if image is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "图片不存在"})

    stored = await db.get(StoredObject, image.stored_object_id)
    if stored is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "对象不存在"})



    storage = get_storage_provider()
    url = await storage.presign_download(stored.bucket, stored.object_key)
    return ok({"url": url})