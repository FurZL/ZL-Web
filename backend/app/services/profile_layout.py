"""个人主页布局草稿与素材权限服务。"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import Image, ProfileImage, StoredObject
from app.models.profile_layout import ProfileLayout
from app.models.user import User
from app.providers.factory import get_storage_provider
from app.services.image_processing import derive_profile_thumb_key

DEFAULT_THEME: dict[str, Any] = {
    "primary": "#6B5CE7",
    "accent": "#F0A6C8",
    "background_type": "gradient",
    "background_key": None,
    "background_blur": 0,
    "card_style": "glass",
}

ALLOWED_SPANS = {
    "bio": {4, 6, 8, 12},
    "quote": {4, 6, 12},
    "featured_photo": {12},
    "photo_wall": {6, 8, 12},
    "gallery_link": {3, 4, 6, 12},
    "links": {3, 4, 6},
    "stats": {3, 4, 6, 12},
    "html_block": {12},
}

MAX_LAYOUT_BYTES = 256 * 1024
MAX_HTML_LENGTH = 24_576
BLOCK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


class ProfileLayoutError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _invalid(message: str) -> ProfileLayoutError:
    return ProfileLayoutError("PROFILE_LAYOUT_INVALID", message)


def _required_string(
    value: Any, *, block_id: str, field: str, max_length: int, allow_empty: bool = True
) -> str:
    if not isinstance(value, str) or (not allow_empty and not value) or len(value) > max_length:
        raise _invalid(f"块 {block_id} 的 {field} 格式无效或超过 {max_length} 字符")
    return value


def _props(raw: Any, block_id: str, block_type: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise _invalid(f"块 {block_id} 的 props 必须是对象")

    if block_type == "bio":
        return {
            "text": _required_string(
                raw.get("text"), block_id=block_id, field="text", max_length=500
            )
        }
    if block_type == "quote":
        return {
            "text": _required_string(
                raw.get("text"), block_id=block_id, field="text", max_length=160
            ),
            "author": _required_string(
                raw.get("author"), block_id=block_id, field="author", max_length=40
            ),
        }
    if block_type == "featured_photo":
        return {
            "object_key": _required_string(
                raw.get("object_key"),
                block_id=block_id,
                field="object_key",
                max_length=1024,
                allow_empty=False,
            ),
            "caption": _required_string(
                raw.get("caption"), block_id=block_id, field="caption", max_length=80
            ),
        }
    if block_type == "photo_wall":
        object_keys = raw.get("object_keys")
        columns = raw.get("columns")
        if not isinstance(object_keys, list) or len(object_keys) > 12:
            raise _invalid(f"块 {block_id} 的 object_keys 必须是最多 12 项的数组")
        if any(not isinstance(key, str) or not key for key in object_keys):
            raise _invalid(f"块 {block_id} 的 object_keys 必须是非空字符串")
        if isinstance(columns, bool) or not isinstance(columns, int) or columns not in (2, 3):
            raise _invalid(f"块 {block_id} 的 columns 只允许 2 或 3")
        return {"object_keys": list(object_keys), "columns": columns}
    if block_type == "gallery_link":
        return {
            "tag": _required_string(raw.get("tag"), block_id=block_id, field="tag", max_length=40),
            "label": _required_string(
                raw.get("label"),
                block_id=block_id,
                field="label",
                max_length=20,
                allow_empty=False,
            ),
        }
    if block_type == "links":
        items = raw.get("items")
        if not isinstance(items, list) or len(items) > 8:
            raise _invalid(f"块 {block_id} 的 items 必须是最多 8 项的数组")
        clean_items = []
        for item in items:
            if not isinstance(item, dict):
                raise _invalid(f"块 {block_id} 的链接项必须是对象")
            label = _required_string(
                item.get("label"),
                block_id=block_id,
                field="label",
                max_length=20,
                allow_empty=False,
            )
            url = _required_string(
                item.get("url"),
                block_id=block_id,
                field="url",
                max_length=300,
                allow_empty=False,
            )
            try:
                parsed_url = urlsplit(url)
            except ValueError:
                raise _invalid(f"块 {block_id} 的链接 URL 只允许 http/https")
            if parsed_url.scheme.lower() not in {"http", "https"} or not parsed_url.netloc:
                raise _invalid(f"块 {block_id} 的链接 URL 只允许 http/https")
            clean_items.append({"label": label, "url": url})
        return {"items": clean_items}
    if block_type == "stats":
        items = raw.get("items")
        allowed_items = {"joined_days", "gallery_image_count"}
        if (
            not isinstance(items, list)
            or len(items) > 2
            or any(not isinstance(item, str) or item not in allowed_items for item in items)
        ):
            raise _invalid(
                f"块 {block_id} 的 items 只允许 joined_days/gallery_image_count，最多 2 项"
            )
        return {"items": list(items)}
    if block_type == "html_block":
        html = _required_string(
            raw.get("html"), block_id=block_id, field="html", max_length=MAX_HTML_LENGTH
        )
        height = raw.get("height")
        if isinstance(height, bool) or not isinstance(height, int) or height not in (200, 400, 600):
            raise _invalid(f"块 {block_id} 的 height 只允许 200、400 或 600")
        return {"html": html, "height": height}
    raise _invalid(f"未知模块类型：{block_id}.type={block_type}")


def validate_blocks(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise _invalid("blocks 必须是数组")
    if len(raw) > settings.profile_layout_max_blocks:
        raise _invalid(f"模块数超过上限 {settings.profile_layout_max_blocks}")

    seen: set[str] = set()
    blocks: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise _invalid("block 必须是对象")
        block_id = item.get("id")
        if not isinstance(block_id, str) or not BLOCK_ID_PATTERN.fullmatch(block_id):
            raise _invalid(f"块 id 非法：{block_id if isinstance(block_id, str) else ''}")
        if block_id in seen:
            raise _invalid(f"块 id 重复：{block_id}")
        seen.add(block_id)

        block_type = item.get("type")
        if not isinstance(block_type, str) or block_type not in ALLOWED_SPANS:
            raise _invalid(
                f"未知模块类型：{block_id}.type={block_type if isinstance(block_type, str) else ''}"
            )
        span = item.get("span")
        if (
            isinstance(span, bool)
            or not isinstance(span, int)
            or span not in ALLOWED_SPANS[block_type]
        ):
            raise _invalid(f"块 {block_id} 的宽度 {span} 不被允许")

        clean_props = _props(item.get("props"), block_id, block_type)
        blocks.append({"id": block_id, "type": block_type, "span": span, "props": clean_props})
    return blocks


def _body_size(body: Any) -> int:
    try:
        encoded = json.dumps(
            body, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        return MAX_LAYOUT_BYTES + 1
    return len(encoded)


def _collect_media_keys(blocks: list[dict[str, Any]], theme: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for block in blocks:
        props = block["props"]
        if block["type"] == "featured_photo":
            keys.add(props["object_key"])
        elif block["type"] == "photo_wall":
            keys.update(props["object_keys"])
    background_key = theme.get("background_key")
    if isinstance(background_key, str) and background_key:
        keys.add(background_key)
    return keys


async def _owned_displayable_images(
    db: AsyncSession, user: User, object_keys: set[str]
) -> dict[str, tuple[ProfileImage, StoredObject]]:
    if not object_keys:
        return {}
    result = await db.execute(
        select(ProfileImage, StoredObject)
        .join(StoredObject, StoredObject.id == ProfileImage.stored_object_id)
        .where(
            ProfileImage.owner_id == user.id,
            ProfileImage.is_displayable.is_(True),
            StoredObject.object_key.in_(object_keys),
        )
    )
    owner_prefix = f"private/profiles/{user.id}/"
    return {
        stored.object_key: (image, stored)
        for image, stored in result.all()
        if stored.object_key.startswith(owner_prefix)
    }


def _layout_theme(layout: ProfileLayout | None) -> dict[str, Any]:
    return {**DEFAULT_THEME, **(layout.theme if layout and layout.theme else {})}


async def _media_payload(
    rows: dict[str, tuple[ProfileImage, StoredObject]],
) -> dict[str, dict[str, Any]]:
    storage = get_storage_provider()
    media: dict[str, dict[str, Any]] = {}
    for object_key, (image, stored) in rows.items():
        thumb_url = None
        if stored.processing_status == "ready":
            thumb_url = await storage.presign_download(
                stored.bucket,
                derive_profile_thumb_key(stored.object_key),
                expires_in=settings.private_url_ttl_seconds,
            )
        display_url = await storage.presign_download(
            stored.bucket,
            stored.object_key,
            expires_in=settings.private_url_ttl_seconds,
        )
        media[object_key] = {
            "thumb_url": thumb_url,
            "display_url": display_url,
            "width": image.width,
            "height": image.height,
        }
    return media


async def _stats(db: AsyncSession, user: User) -> dict[str, int]:
    created_at = user.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    joined_days = (datetime.now(UTC) - created_at).days
    # Count reviewed public Gallery images only; private profile images are excluded.
    gallery_image_count = await db.scalar(
        select(func.count(Image.id)).where(
            Image.uploader_id == user.id,
            Image.moderation_status == "approved",
            Image.is_public.is_(True),
        )
    )
    return {"joined_days": joined_days, "gallery_image_count": gallery_image_count or 0}


async def get_layout_payload(db: AsyncSession, user: User) -> dict[str, Any]:
    layout = await db.get(ProfileLayout, user.id)
    theme = _layout_theme(layout)
    draft_blocks = layout.draft_blocks if layout else []
    published_blocks = layout.published_blocks if layout else None
    all_blocks = draft_blocks + (published_blocks or [])
    rows = await _owned_displayable_images(db, user, _collect_media_keys(all_blocks, theme))
    return {
        "theme": theme,
        "draft_blocks": draft_blocks,
        "published_blocks": published_blocks,
        "is_public": layout.is_public if layout else True,
        "max_blocks": settings.profile_layout_max_blocks,
        "media": await _media_payload(rows),
        "media_expires_in": settings.private_url_ttl_seconds,
        "stats": await _stats(db, user),
    }


async def put_layout(db: AsyncSession, user: User, body: Any) -> dict[str, Any]:
    if _body_size(body) > MAX_LAYOUT_BYTES:
        raise ProfileLayoutError("PROFILE_LAYOUT_TOO_LARGE", "布局内容超过 256 KB", status_code=422)
    if not isinstance(body, dict):
        raise _invalid("请求体必须是对象")

    blocks = validate_blocks(body.get("blocks"))
    is_public = body.get("is_public")
    if "is_public" in body and not isinstance(is_public, bool):
        raise _invalid("is_public 必须是布尔值")

    layout = await db.get(ProfileLayout, user.id)
    theme = _layout_theme(layout)
    requested_keys = _collect_media_keys(blocks, theme)
    available = await _owned_displayable_images(db, user, requested_keys)
    missing_key = next((key for key in requested_keys if key not in available), None)
    if missing_key is not None:
        raise _invalid(f"素材不可展示或不属于本人：{missing_key}")

    if layout is None:
        layout = ProfileLayout(
            user_id=user.id,
            draft_blocks=blocks,
            published_blocks=None,
            is_public=True if is_public is None else is_public,
            theme=dict(DEFAULT_THEME),
        )
        db.add(layout)
    else:
        layout.draft_blocks = blocks
        if is_public is not None:
            layout.is_public = is_public

    await db.commit()
    await db.refresh(layout)
    return await get_layout_payload(db, user)


async def set_image_displayable(
    db: AsyncSession, user: User, image_id: uuid.UUID, is_displayable: bool
) -> dict[str, Any]:
    image = await db.get(ProfileImage, image_id)
    if image is None or image.owner_id != user.id:
        raise ProfileLayoutError("PROFILE_IMAGE_NOT_FOUND", "图片不存在", status_code=404)
    image.is_displayable = is_displayable
    await db.commit()
    await db.refresh(image)
    return {"id": str(image.id), "is_displayable": image.is_displayable}
