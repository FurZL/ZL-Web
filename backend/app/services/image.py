"""图片服务：上传意图、上传完成、列表。

上传流程（架构文档 4.3）：
1. 前端申请 upload-intent，后端校验权限/MIME/大小，签发随机 Object Key + 预签名 URL。
2. 前端直接 PUT 到 COS。
3. 前端 upload-complete，后端 HEAD 复核对象，写入 StoredObject + Image 元数据。

数据库只存 bucket + object_key，公开 URL 由后端动态生成，不存固定 CDN 域名。
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import Image, StoredObject
from app.models.user import User
from app.providers.factory import get_storage_provider
from app.services import image_processing

# 图片类型白名单（拒绝 SVG/HTML/脚本/压缩包等高风险类型）
ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
}


class ImageError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _new_key_prefix(purpose: str, user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    if purpose == "gallery":
        return f"public/gallery/original/{now.year:04d}/{now.month:02d}"
    if purpose == "profile":
        return f"private/profiles/{user_id}"
    raise ImageError("INVALID_PURPOSE", f"不支持的用途: {purpose}")


def _generate_object_key(purpose: str, user_id: uuid.UUID) -> tuple[str, str]:
    """返回 (object_key, visibility)。"""
    prefix = _new_key_prefix(purpose, user_id)
    token = secrets.token_hex(16)
    key = f"{prefix}/{token}"
    visibility = "public" if purpose == "gallery" else "private"
    return key, visibility


async def create_upload_intent(
    *,
    user: User,
    filename: str,
    mime_type: str,
    size_bytes: int,
    purpose: str,
) -> dict:
    # MIME 白名单校验（也要防大小写差异）
    mime = mime_type.lower()
    if mime not in ALLOWED_MIME:
        raise ImageError("UNSUPPORTED_TYPE", "仅支持 JPG / PNG / WebP / GIF / AVIF 图片")

    # 大小校验
    if size_bytes <= 0 or size_bytes > settings.upload_max_bytes:
        raise ImageError("FILE_TOO_LARGE", f"文件大小超限（最大 {settings.upload_max_bytes // 1024 // 1024}MB）")

    object_key, visibility = _generate_object_key(purpose, user.id)

    storage = get_storage_provider()
    presign = await storage.presign_upload(
        bucket=storage.bucket,
        object_key=object_key,
        content_type=mime,
        max_bytes=size_bytes,
        expires_in=settings.private_url_ttl_seconds,
    )

    return {
        "storage_provider": settings.storage_provider,
        "bucket": storage.bucket,
        "object_key": object_key,
        "visibility": visibility,
        "upload_url": presign.url,
        "expires_in": presign.expires_in,
    }


async def complete_upload(
    db: AsyncSession,
    *,
    user: User,
    object_key: str,
    bucket: str,
    original_name: str,
    purpose: str,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Image:
    # 前缀校验：object_key 必须位于该用户该用途的前缀下，防止引用别人的对象
    if purpose == "gallery":
        valid_prefix = "public/gallery/original/"
    elif purpose == "profile":
        valid_prefix = f"private/profiles/{user.id}/"
    else:
        raise ImageError("INVALID_PURPOSE", f"不支持的用途: {purpose}")

    if not object_key.startswith(valid_prefix):
        raise ImageError("INVALID_KEY", "无效的对象 Key")

    storage = get_storage_provider()
    head = await storage.head_object(bucket or storage.bucket, object_key)
    if not head.exists:
        raise ImageError("OBJECT_NOT_FOUND", "对象不存在，请重新上传")

    # 创建 StoredObject
    visibility = "public" if purpose == "gallery" else "private"
    stored = StoredObject(
        provider=settings.storage_provider,
        bucket=bucket or storage.bucket,
        object_key=object_key,
        visibility=visibility,
        mime_type=None,  # 后续由处理任务补充精确 MIME/尺寸
        size_bytes=head.size_bytes,
        processing_status="pending",
        created_by=user.id,
    )
    db.add(stored)
    await db.flush()

    # 创建 Image
    tag_str = ",".join([t.strip() for t in (tags or []) if t.strip()]) or None
    image = Image(
        stored_object_id=stored.id,
        original_name=original_name,
        uploader_id=user.id,
        tags=tag_str,
        description=description,
        # 摄影师/管理员上传公开图片直接发布；普通成员无权上传公开图（权限已在依赖层校验）
        moderation_status="approved" if purpose == "gallery" else "pending",
        is_public=(purpose == "gallery"),
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    # 公开图片触发后台处理（生成展示图/缩略图）
    if purpose == "gallery":
        from app.workers.image_worker import enqueue_image

        enqueue_image(image.id)

    return image


async def list_public_images(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    page = max(1, page)
    page_size = min(max(1, page_size), 50)

    stmt = (
        select(Image)
        .where(Image.is_public.is_(True), Image.moderation_status == "approved")
        .order_by(Image.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    images = (await db.scalars(stmt)).all()

    total = await db.scalar(
        select(func.count()).select_from(Image).where(
            Image.is_public.is_(True), Image.moderation_status == "approved"
        )
    ) or 0

    return {
        "items": [await _image_to_dict(db, img) for img in images],
        "pagination": {"page": page, "page_size": page_size, "total": int(total)},
    }


async def _image_to_dict(db: AsyncSession, image: Image) -> dict:
    stored = await db.get(StoredObject, image.stored_object_id)
    storage = get_storage_provider()
    uploader = await db.get(User, image.uploader_id)

    object_key = stored.object_key if stored else None
    url = storage.public_url(stored.bucket, object_key) if stored else None

    # 派生图 URL（由 object_key 推导；未处理完成时可能 404，前端可回退原图）
    display_url = thumb_url = None
    if object_key and stored and stored.processing_status == "ready":
        try:
            display_url = storage.public_url(
                stored.bucket, image_processing.derive_display_key(object_key)
            )
            thumb_url = storage.public_url(
                stored.bucket, image_processing.derive_thumb_key(object_key)
            )
        except ValueError:
            pass

    return {
        "id": str(image.id),
        "url": url,
        "display_url": display_url,
        "thumb_url": thumb_url,
        "object_key": object_key,
        "original_name": image.original_name,
        "title": image.original_name or "未命名",
        "description": image.description,
        "tags": [t for t in (image.tags or "").split(",") if t],
        "photographer": uploader.display_name if uploader else "未知",
        "moderation_status": image.moderation_status,
        "is_public": image.is_public,
        "width": image.width,
        "height": image.height,
        "uploaded_at": image.created_at.isoformat() if image.created_at else None,
        "processing_status": stored.processing_status if stored else None,
    }