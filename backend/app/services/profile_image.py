"""个人空间私有相册服务。

与公开 Gallery 的差异（架构文档 3.3 / 4.1）：
- 私有图存 private/profiles/{user_id}/ 前缀，仅本人可见。
- 下载不直接给公开 URL，而是后端鉴权后签发短时效签名 URL。
- 上传意图/完成复用 image_service 的校验，但落库到 ProfileImage 表。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import ProfileImage, StoredObject
from app.models.user import User
from app.providers.factory import get_storage_provider
from app.services.image import ImageError, complete_upload, create_upload_intent, sanitize_filename


async def create_profile_upload_intent(
    *, user: User, filename: str, mime_type: str, size_bytes: int
) -> dict:
    return await create_upload_intent(
        user=user,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        purpose="profile",
    )


async def complete_profile_upload(
    db: AsyncSession,
    *,
    user: User,
    object_key: str,
    bucket: str,
    original_name: str,
    description: str | None = None,
) -> ProfileImage:
    # 前缀校验：private/profiles/{user_id}/
    valid_prefix = f"private/profiles/{user.id}/"
    if not object_key.startswith(valid_prefix):
        raise ImageError("INVALID_KEY", "无效的对象 Key")

    storage = get_storage_provider()
    head = await storage.head_object(bucket or storage.bucket, object_key)
    if not head.exists:
        raise ImageError("OBJECT_NOT_FOUND", "对象不存在，请重新上传")

    stored = StoredObject(
        provider=settings.storage_provider,
        bucket=bucket or storage.bucket,
        object_key=object_key,
        visibility="private",
        mime_type=None,
        size_bytes=head.size_bytes,
        processing_status="pending",
        created_by=user.id,
    )
    db.add(stored)
    await db.flush()

    image = ProfileImage(
        owner_id=user.id,
        stored_object_id=stored.id,
        original_name=sanitize_filename(original_name),
        description=description,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    # 私有图也做缩略图处理（复用后台 worker），但不对外公开
    from app.workers.image_worker import enqueue_profile_image

    enqueue_profile_image(image.id)

    return image


async def list_my_profile_images(
    db: AsyncSession, user: User
) -> dict:
    stmt = (
        select(ProfileImage)
        .where(ProfileImage.owner_id == user.id)
        .order_by(ProfileImage.created_at.desc())
    )
    images = (await db.scalars(stmt)).all()

    items = []
    storage = get_storage_provider()
    for img in images:
        stored = await db.get(StoredObject, img.stored_object_id)
        if stored is None:
            continue

        # 私有内容不公开，前端展示时签发短时效签名 URL
        thumb_url = None
        if stored.processing_status == "ready":
            try:
                from app.services.image_processing import derive_profile_thumb_key

                thumb_key = derive_profile_thumb_key(stored.object_key)
                thumb_url = await storage.presign_download(stored.bucket, thumb_key)
            except Exception:
                thumb_url = None

        items.append({
            "id": str(img.id),
            "original_name": img.original_name,
            "title": img.description or "未命名",
            "description": img.description,
            "width": img.width,
            "height": img.height,
            "created_at": img.created_at.isoformat() if img.created_at else None,
            "processing_status": stored.processing_status if stored else None,
            "thumb_url": thumb_url,
        })
    return {"items": items, "total": len(items)}


async def get_profile_image_signed_url(
    db: AsyncSession, *, user: User, image_id: uuid.UUID
) -> dict:
    image = await db.get(ProfileImage, image_id)
    if image is None or image.owner_id != user.id:
        raise ImageError("NOT_FOUND", "图片不存在", 404)

    stored = await db.get(StoredObject, image.stored_object_id)
    if stored is None:
        raise ImageError("NOT_FOUND", "对象不存在", 404)

    storage = get_storage_provider()
    url = await storage.presign_download(stored.bucket, stored.object_key)
    return {"url": url, "expires_in": settings.private_url_ttl_seconds}


async def delete_profile_image(
    db: AsyncSession, *, user: User, image_id: uuid.UUID
) -> None:
    image = await db.get(ProfileImage, image_id)
    if image is None or image.owner_id != user.id:
        raise ImageError("NOT_FOUND", "图片不存在", 404)

    stored = await db.get(StoredObject, image.stored_object_id)
    if stored:
        storage = get_storage_provider()
        try:
            await storage.delete_object(stored.bucket, stored.object_key)
            # 同步删除缩略图，避免孤儿对象
            if stored.processing_status == "ready":
                from app.services.image_processing import derive_profile_thumb_key

                thumb_key = derive_profile_thumb_key(stored.object_key)
                await storage.delete_object(stored.bucket, thumb_key)
        except Exception:
            pass
        await db.delete(stored)
    await db.delete(image)
    await db.commit()