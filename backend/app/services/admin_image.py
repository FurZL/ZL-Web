"""图片管理服务：管理端列表、审核、删除、标签编辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import Image, StoredObject
from app.models.user import User
from app.services.image import ImageError, _image_to_dict


async def list_all_images(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    is_public: bool | None = None,
) -> dict:
    page = max(1, page)
    page_size = min(max(1, page_size), 50)

    conditions = []
    if status:
        conditions.append(Image.moderation_status == status)
    if is_public is not None:
        conditions.append(Image.is_public.is_(is_public))

    stmt = select(Image).order_by(Image.created_at.desc())
    count_stmt = select(func.count()).select_from(Image)
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    images = (
        await db.scalars(stmt.offset((page - 1) * page_size).limit(page_size))
    ).all()
    total = await db.scalar(count_stmt) or 0

    return {
        "items": [await _image_to_dict(db, img) for img in images],
        "pagination": {"page": page, "page_size": page_size, "total": int(total)},
    }


async def set_moderation(
    db: AsyncSession, image_id: uuid.UUID, moderation_status: str
) -> dict:
    if moderation_status not in ("pending", "approved", "rejected"):
        raise ImageError("INVALID_STATUS", "无效的审核状态")
    image = await db.get(Image, image_id)
    if image is None:
        raise ImageError("NOT_FOUND", "图片不存在", 404)
    image.moderation_status = moderation_status
    if moderation_status == "approved":
        image.is_public = True
    elif moderation_status == "rejected":
        image.is_public = False
    await db.commit()
    await db.refresh(image)
    return await _image_to_dict(db, image)


async def set_visibility(db: AsyncSession, image_id: uuid.UUID, is_public: bool) -> dict:
    image = await db.get(Image, image_id)
    if image is None:
        raise ImageError("NOT_FOUND", "图片不存在", 404)
    image.is_public = is_public
    await db.commit()
    await db.refresh(image)
    return await _image_to_dict(db, image)


async def update_tags(
    db: AsyncSession, image_id: uuid.UUID, tags: list[str]
) -> dict:
    image = await db.get(Image, image_id)
    if image is None:
        raise ImageError("NOT_FOUND", "图片不存在", 404)
    image.tags = ",".join([t.strip() for t in tags if t.strip()]) or None
    await db.commit()
    await db.refresh(image)
    return await _image_to_dict(db, image)


async def delete_image(db: AsyncSession, image_id: uuid.UUID) -> None:
    image = await db.get(Image, image_id)
    if image is None:
        raise ImageError("NOT_FOUND", "图片不存在", 404)

    stored = await db.get(StoredObject, image.stored_object_id) if image.stored_object_id else None
    if stored:
        try:
            from app.providers.factory import get_storage_provider

            storage = get_storage_provider()
            await storage.delete_object(stored.bucket, stored.object_key)
            # 删除派生图
            from app.services import image_processing

            for derive in (image_processing.derive_display_key, image_processing.derive_thumb_key):
                try:
                    await storage.delete_object(stored.bucket, derive(stored.object_key))
                except Exception:
                    pass
        except Exception:
            pass
        await db.delete(stored)

    await db.delete(image)
    await db.commit()


async def get_stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count()).select_from(Image)) or 0
    pending = await db.scalar(
        select(func.count()).select_from(Image).where(Image.moderation_status == "pending")
    ) or 0
    approved = await db.scalar(
        select(func.count()).select_from(Image).where(Image.moderation_status == "approved")
    ) or 0
    rejected = await db.scalar(
        select(func.count()).select_from(Image).where(Image.moderation_status == "rejected")
    ) or 0
    return {
        "total": int(total),
        "pending": int(pending),
        "approved": int(approved),
        "rejected": int(rejected),
    }
