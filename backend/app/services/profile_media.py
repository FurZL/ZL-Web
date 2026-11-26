"""Short-lived capabilities for private profile media."""

from datetime import datetime, timedelta, timezone
import uuid

import jwt
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image import ProfileImage, StoredObject
from app.models.profile_layout import ProfileLayout
from app.models.user import User
from app.services.image_processing import derive_profile_thumb_key


def media_url(image: ProfileImage, variant: str, scope: str) -> str:
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": str(image.owner_id), "image": str(image.id), "variant": variant,
        "scope": scope, "purpose": "profile_media", "iat": now,
        "exp": now + timedelta(seconds=settings.private_url_ttl_seconds),
    }, settings.secret_key, algorithm="HS256")
    base = settings.public_api_base_url.rstrip("/")
    return f"{base}{settings.api_v1_prefix}/profile/media/{image.id}/{variant}?ticket={token}"


async def resolve_media(db: AsyncSession, image_id: uuid.UUID, variant: str, ticket: str):
    not_found = HTTPException(status_code=404, detail="图片不存在或链接已失效")
    try:
        claims = jwt.decode(ticket, settings.secret_key, algorithms=["HS256"], options={"require": ["exp", "iat", "sub"]})
    except jwt.PyJWTError:
        raise not_found
    if (claims.get("purpose") != "profile_media" or claims.get("image") != str(image_id)
            or claims.get("variant") != variant or variant not in ("thumb", "original")
            or claims.get("scope") not in ("owner", "public")):
        raise not_found
    image = await db.get(ProfileImage, image_id)
    if image is None or str(image.owner_id) != claims["sub"]:
        raise not_found
    user = await db.get(User, image.owner_id)
    stored = await db.get(StoredObject, image.stored_object_id)
    if (user is None or user.status != "active" or not user.is_active or stored is None
            or stored.deleted_at is not None or stored.visibility != "private"
            or (stored.size_bytes is not None and stored.size_bytes > settings.upload_max_bytes)
            or not stored.object_key.startswith(f"private/profiles/{image.owner_id}/")):
        raise not_found
    if variant == "thumb" and stored.processing_status != "ready":
        raise not_found
    if claims["scope"] == "public":
        from app.services.profile_layout import ProfileLayoutError, _collect_media_keys, _layout_theme, validate_blocks
        layout = await db.get(ProfileLayout, image.owner_id)
        if not image.is_displayable or layout is None or not layout.is_public or layout.published_blocks is None:
            raise not_found
        try:
            keys = _collect_media_keys(validate_blocks(layout.published_blocks), _layout_theme(layout))
        except (ProfileLayoutError, ValueError, KeyError, TypeError):
            raise not_found
        if stored.object_key not in keys:
            raise not_found
    key = derive_profile_thumb_key(stored.object_key) if variant == "thumb" else stored.object_key
    allowed_mimes = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
    mime = stored.mime_type if stored.mime_type in allowed_mimes else "application/octet-stream"
    return stored.bucket, key, "image/webp" if variant == "thumb" else mime
