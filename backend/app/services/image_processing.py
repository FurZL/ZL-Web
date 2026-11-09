"""图片处理服务（后台任务）：下载原图 → 解码校验 → 生成展示图与缩略图 → 上传派生图。

设计：
- 派生图 Object Key 由原图 Key 确定性推导，不额外建表：
  public/gallery/original/{yyyy}/{mm}/{token}
    -> public/gallery/derived/{yyyy}/{mm}/{token}/display.webp
    -> public/gallery/derived/{yyyy}/{mm}/{token}/thumb.webp
- 只处理 public gallery；私有图片后续按需扩展。
- 使用 Pillow，解码前设置最大像素数防解压炸弹。
"""

from __future__ import annotations

import asyncio
import io
import logging
from pathlib import PurePosixPath

from PIL import Image as PILImage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import Image, StoredObject
from app.providers.factory import get_storage_provider

logger = logging.getLogger(__name__)

# 保护：解压炸弹阈值
PILImage.MAX_IMAGE_PIXELS = settings.image_max_pixels


def _derive_dir(object_key: str) -> str:
    p = PurePosixPath(object_key)
    # public/gallery/original/{yyyy}/{mm}/{token}
    parts = p.parts
    if len(parts) < 4 or parts[0] != "public" or parts[2] != "original":
        raise ValueError(f"非 gallery 原图 Key: {object_key}")
    token = parts[-1]
    year, month = parts[-3], parts[-2]
    return f"public/gallery/derived/{year}/{month}/{token}"


def derive_display_key(object_key: str) -> str:
    # key 内嵌尺寸参数：参数变更会生成新 key，避免 immutable 缓存残留旧图
    px = settings.image_display_max_px
    return f"{_derive_dir(object_key)}/display_{px}.webp"


def derive_thumb_key(object_key: str) -> str:
    px = settings.image_thumb_max_px
    return f"{_derive_dir(object_key)}/thumb_{px}.webp"


def derive_profile_thumb_key(object_key: str) -> str:
    """私有图缩略图 key：private/profiles/{user_id}/{token} -> private/profiles/{user_id}/thumb/{token}.webp"""
    p = PurePosixPath(object_key)
    parts = p.parts
    if len(parts) < 4 or parts[0] != "private" or parts[1] != "profiles":
        raise ValueError(f"非 profile 原图 Key: {object_key}")
    user_id = parts[2]
    token = parts[-1]
    px = settings.image_thumb_max_px
    return f"private/profiles/{user_id}/thumb_{px}/{token}.webp"


def _decode(data: bytes) -> PILImage.Image:
    img = PILImage.open(io.BytesIO(data))
    img.load()
    return img


def _resize(img: PILImage.Image, max_px: int) -> PILImage.Image:
    w, h = img.size
    longest = max(w, h)
    if longest <= max_px:
        return img.copy()
    ratio = max_px / longest
    new_size = (max(1, round(w * ratio)), max(1, round(h * ratio)))
    return img.resize(new_size, PILImage.LANCZOS)


def _encode_webp(img: PILImage.Image, quality: int) -> bytes:
    # 统一转 RGB（丢弃 alpha，简化；如需透明可改 RGBA）
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


async def process_image(db: AsyncSession, image_id) -> None:
    """处理单张图：生成派生图并更新元数据。"""
    from app.models.image import Image as ImageModel

    image = await db.get(ImageModel, image_id)
    if image is None:
        return

    stored = await db.get(StoredObject, image.stored_object_id)
    if stored is None:
        return

    # 标记处理中
    stored.processing_status = "processing"
    await db.commit()

    storage = get_storage_provider()
    try:
        original = await storage.get_object_bytes(stored.bucket, stored.object_key)

        # 解码 + 校验（PIL 已用 MAX_IMAGE_PIXELS 拦截超大图）
        img = await asyncio.to_thread(_decode, original)
        width, height = img.size

        # 生成展示图
        display = await asyncio.to_thread(
            _resize, img, settings.image_display_max_px
        )
        display_bytes = await asyncio.to_thread(
            _encode_webp, display, settings.image_quality
        )
        display_key = derive_display_key(stored.object_key)

        # 生成缩略图
        thumb = await asyncio.to_thread(_resize, img, settings.image_thumb_max_px)
        thumb_bytes = await asyncio.to_thread(
            _encode_webp, thumb, settings.image_quality
        )
        thumb_key = derive_thumb_key(stored.object_key)

        # 上传派生图
        await storage.put_object_bytes(stored.bucket, display_key, display_bytes, "image/webp")
        await storage.put_object_bytes(stored.bucket, thumb_key, thumb_bytes, "image/webp")

        # 更新元数据
        image.width = width
        image.height = height
        stored.processing_status = "ready"
        await db.commit()

        logger.info("图片处理完成 image_id=%s %sx%s", image.id, width, height)
    except Exception as exc:
        logger.exception("图片处理失败 image_id=%s: %s", image.id, exc)
        stored.processing_status = "failed"
        await db.commit()
        raise


async def process_profile_image(db: AsyncSession, image_id) -> None:
    """处理私有相册图：生成缩略图，更新 ProfileImage 尺寸。"""
    from app.models.image import ProfileImage as ProfileImageModel

    image = await db.get(ProfileImageModel, image_id)
    if image is None:
        return

    stored = await db.get(StoredObject, image.stored_object_id)
    if stored is None:
        return

    stored.processing_status = "processing"
    await db.commit()

    storage = get_storage_provider()
    try:
        original = await storage.get_object_bytes(stored.bucket, stored.object_key)
        img = await asyncio.to_thread(_decode, original)
        width, height = img.size

        thumb = await asyncio.to_thread(_resize, img, settings.image_thumb_max_px)
        thumb_bytes = await asyncio.to_thread(_encode_webp, thumb, settings.image_quality)
        thumb_key = derive_profile_thumb_key(stored.object_key)
        await storage.put_object_bytes(stored.bucket, thumb_key, thumb_bytes, "image/webp")

        image.width = width
        image.height = height
        stored.processing_status = "ready"
        await db.commit()
        logger.info("私有图处理完成 profile_image_id=%s %sx%s", image.id, width, height)
    except Exception as exc:
        logger.exception("私有图处理失败 profile_image_id=%s: %s", image.id, exc)
        stored.processing_status = "failed"
        await db.commit()
        raise