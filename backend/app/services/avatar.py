"""头像上传服务。

- 头像存 public/avatars/{user_id}/ 前缀，公开展示。
- user.avatar_url 存 object_key，API 响应时动态生成公开 URL。
- 上传复用 image_service 的 MIME/大小校验和预签名机制。
"""

from __future__ import annotations

import logging
import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.providers.factory import get_storage_provider
from app.services.image import ALLOWED_MIME, ImageError

logger = logging.getLogger(__name__)

# 头像最大 5MB
AVATAR_MAX_BYTES = 5 * 1024 * 1024


def _generate_avatar_key(user_id: uuid.UUID) -> str:
    token = secrets.token_hex(16)
    return f"public/avatars/{user_id}/{token}"


async def create_avatar_upload_intent(
    *, user: User, filename: str, mime_type: str, size_bytes: int
) -> dict:
    mime = mime_type.lower()
    if mime not in ALLOWED_MIME:
        raise ImageError("UNSUPPORTED_TYPE", "仅支持 JPG / PNG / WebP / GIF / AVIF 图片")
    if size_bytes <= 0 or size_bytes > AVATAR_MAX_BYTES:
        raise ImageError("FILE_TOO_LARGE", f"头像大小不能超过 {AVATAR_MAX_BYTES // 1024 // 1024}MB")

    object_key = _generate_avatar_key(user.id)
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
        "upload_url": presign.url,
        "expires_in": presign.expires_in,
    }


async def complete_avatar_upload(
    db: AsyncSession,
    *,
    user: User,
    object_key: str,
    bucket: str,
) -> dict:
    valid_prefix = f"public/avatars/{user.id}/"
    if not object_key.startswith(valid_prefix):
        raise ImageError("INVALID_KEY", "无效的对象 Key")

    storage = get_storage_provider()
    head = await storage.head_object(bucket or storage.bucket, object_key)
    if not head.exists:
        raise ImageError("OBJECT_NOT_FOUND", "对象不存在，请重新上传")

    # 如果用户已有头像，删除旧对象
    old_key = user.avatar_url
    if old_key and old_key.startswith("public/avatars/"):
        try:
            await storage.delete_object(storage.bucket, old_key)
        except Exception:
            logger.warning("删除旧头像失败 key=%s", old_key, exc_info=True)

    user.avatar_url = object_key
    await db.commit()
    await db.refresh(user)
    return {"avatar_url": get_avatar_public_url(user)}


def get_avatar_public_url(user: User) -> str | None:
    """从 object_key 生成公开 URL。"""
    if not user.avatar_url or not user.avatar_url.startswith("public/avatars/"):
        return user.avatar_url  # 兼容旧的外部 URL
    storage = get_storage_provider()
    return storage.public_url(storage.bucket, user.avatar_url)


async def delete_avatar(db: AsyncSession, *, user: User) -> None:
    if not user.avatar_url:
        return
    storage = get_storage_provider()
    if user.avatar_url.startswith("public/avatars/"):
        try:
            await storage.delete_object(storage.bucket, user.avatar_url)
        except Exception:
            logger.warning("删除头像失败 key=%s", user.avatar_url, exc_info=True)
    user.avatar_url = None
    await db.commit()
