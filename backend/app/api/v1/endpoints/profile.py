"""个人空间端点：私有相册（本人鉴权）。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import error_to_http, ok, parse_uuid
from app.core.database import get_db
from app.models.user import User
from app.schemas.image import (
    ProfileUploadCompleteRequest,
    ProfileUploadIntentRequest,
)
from app.schemas.profile_layout import ProfileImageDisplayPatch, ProfileTheme
from app.services import avatar as avatar_service
from app.services import profile_image as profile_image_service
from app.services import profile_layout as profile_layout_service
from app.services import third_party_auth
from app.services import profile_media
from app.providers.factory import get_storage_provider
from app.services.image import ImageError

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/media/{image_id}/{variant}")
async def profile_media_content(
    image_id: uuid.UUID, variant: str, ticket: str,
    db: AsyncSession = Depends(get_db),
):
    bucket, key, mime = await profile_media.resolve_media(db, image_id, variant, ticket)
    data = await get_storage_provider().get_object_bytes(bucket, key)
    if mime == "application/octet-stream":
        from io import BytesIO
        from PIL import Image as PillowImage

        try:
            with PillowImage.open(BytesIO(data)) as image:
                mime = PillowImage.MIME.get(image.format, mime)
        except (OSError, ValueError):
            raise HTTPException(status_code=404, detail="图片不可用")
    return Response(content=data, media_type=mime, headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    })


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return ok({
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "bio": user.bio or "",
        "avatar_url": avatar_service.get_avatar_public_url(user),
        "role": user.role,
        "status": user.status,
    })


@router.get("/me/third-party")
async def my_third_party_bindings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bindings = await third_party_auth.list_bindings(db, user)
    return ok({"items": bindings})


@router.delete("/me/third-party/{provider}")
async def delete_my_third_party_binding(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if provider not in third_party_auth.SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail={"code": "OAUTH_PROVIDER_UNSUPPORTED", "message": "暂不支持该登录方式"},
        )
    await third_party_auth.unbind_provider(db, user, provider)
    return ok({"message": "已解绑"})


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


@router.put("/me")
async def update_me(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.display_name is not None:
        name = body.display_name.strip()
        if not name or len(name) > 64:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_NAME", "message": "昵称不能为空且不超过 64 字"},
            )
        user.display_name = name
    if body.bio is not None:
        user.bio = body.bio[:500] or None
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url[:500] or None

    await db.commit()
    await db.refresh(user)
    return ok({
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "bio": user.bio or "",
        "avatar_url": avatar_service.get_avatar_public_url(user),
        "role": user.role,
        "status": user.status,
    })


class AvatarUploadCompleteRequest(BaseModel):
    object_key: str
    bucket: str = ""


@router.post("/me/avatar/upload-intent")
async def avatar_upload_intent(
    body: dict = Body(...),
    user: User = Depends(get_current_user),
):
    filename = body.get("filename", "avatar")
    mime_type = body.get("mime_type", "image/png")
    size_bytes = body.get("size_bytes", 0)
    try:
        intent = await avatar_service.create_avatar_upload_intent(
            user=user,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(intent)


@router.post("/me/avatar/upload-complete")
async def avatar_upload_complete(
    body: AvatarUploadCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await avatar_service.complete_avatar_upload(
            db, user=user, object_key=body.object_key, bucket=body.bucket
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.delete("/me/avatar")
async def avatar_delete(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await avatar_service.delete_avatar(db, user=user)
    return ok({"avatar_url": None})


@router.get("/me/images")
async def my_images(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await profile_image_service.list_my_profile_images(db, user)
    return ok(result)


@router.get("/me/layout")
async def get_my_layout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ok(await profile_layout_service.get_layout_payload(db, user))


@router.put("/me/layout")
async def put_my_layout(
    body: Any = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await profile_layout_service.put_layout(db, user, body)
    except profile_layout_service.ProfileLayoutError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/me/layout/publish")
async def publish_my_layout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await profile_layout_service.publish_layout(db, user)
    except profile_layout_service.ProfileLayoutError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/me/layout/discard")
async def discard_my_layout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ok(await profile_layout_service.discard_layout(db, user))


@router.put("/me/theme")
async def put_my_theme(
    body: Any = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        theme = ProfileTheme.model_validate(body)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROFILE_THEME_INVALID", "message": "主题配置格式无效"},
        )
    try:
        result = await profile_layout_service.put_theme(db, user, theme.model_dump())
    except profile_layout_service.ProfileLayoutError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.get("/me/media")
async def get_my_profile_media(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ok(await profile_layout_service.get_media_options(db, user))


@router.patch("/me/images/{image_id}")
async def patch_profile_image_displayable(
    image_id: str,
    body: ProfileImageDisplayPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        parsed_image_id = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"code": "PROFILE_IMAGE_NOT_FOUND", "message": "图片不存在"},
        )
    try:
        result = await profile_layout_service.set_image_displayable(
            db, user, parsed_image_id, body.is_displayable
        )
    except profile_layout_service.ProfileLayoutError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/me/images/upload-intent")
async def upload_intent(
    body: ProfileUploadIntentRequest,
    user: User = Depends(get_current_user),
):
    try:
        intent = await profile_image_service.create_profile_upload_intent(
            user=user,
            filename=body.filename,
            mime_type=body.mime_type,
            size_bytes=body.size_bytes,
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(intent)


@router.post("/me/images/upload-complete")
async def upload_complete(
    body: ProfileUploadCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        image = await profile_image_service.complete_profile_upload(
            db,
            user=user,
            object_key=body.object_key,
            bucket=body.bucket,
            original_name=body.original_name or body.object_key.rsplit("/", 1)[-1],
            description=body.description,
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"id": str(image.id), "original_name": image.original_name})


@router.get("/me/images/{image_id}/url")
async def image_signed_url(
    image_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await profile_image_service.get_profile_image_signed_url(
            db, user=user, image_id=parse_uuid(image_id)
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.delete("/me/images/{image_id}")
async def delete_image(
    image_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await profile_image_service.delete_profile_image(
            db, user=user, image_id=parse_uuid(image_id)
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"message": "已删除"})


@router.get("/members")
async def list_members(db: AsyncSession = Depends(get_db)):
    """公开成员列表（仅 active 用户，不含邮箱/手机等隐私）。"""
    from sqlalchemy import select

    users = (
        await db.scalars(
            select(User)
            .where(User.status == "active")
            .order_by(User.created_at.asc())
        )
    ).all()
    return ok({"items": [
        {
            "id": str(u.id),
            "username": u.username,
            "display_name": u.display_name,
            "role": u.role,
            "bio": u.bio or "",
            "avatar_url": avatar_service.get_avatar_public_url(u),
        }
        for u in users
    ]})


@router.get("/{username}/page")
async def get_public_profile_page(username: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await profile_layout_service.get_public_page_payload(db, username)
    except profile_layout_service.ProfileLayoutError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.get("/{user_id}")
async def public_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    uid = parse_uuid(user_id)
    u = await db.get(User, uid)
    if u is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})
    # 公开资料不泄露 email/手机号等隐私
    return ok(
        {
            "id": str(u.id),
            "username": u.username,
            "display_name": u.display_name,
            "role": u.role,
        }
    )
