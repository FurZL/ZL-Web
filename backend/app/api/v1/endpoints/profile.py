"""个人空间端点：私有相册（本人鉴权）。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import error_to_http, ok, parse_uuid
from app.core.database import get_db
from app.models.user import User
from app.schemas.image import (
    ProfileUploadCompleteRequest,
    ProfileUploadIntentRequest,
)
from app.services import profile_image as profile_image_service
from app.services.image import ImageError

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return ok({
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "bio": user.bio or "",
        "avatar_url": user.avatar_url,
        "role": user.role,
        "status": user.status,
    })


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
            raise HTTPException(status_code=400, detail={"code": "INVALID_NAME", "message": "昵称不能为空且不超过 64 字"})
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
        "avatar_url": user.avatar_url,
        "role": user.role,
        "status": user.status,
    })


@router.get("/me/images")
async def my_images(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await profile_image_service.list_my_profile_images(db, user)
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
        await profile_image_service.delete_profile_image(db, user=user, image_id=parse_uuid(image_id))
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
            "avatar_url": u.avatar_url,
        }
        for u in users
    ]})


@router.get("/{user_id}")
async def public_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    uid = parse_uuid(user_id)
    u = await db.get(User, uid)
    if u is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})
    # 公开资料不泄露 email/手机号等隐私
    return ok({"id": str(u.id), "username": u.username, "display_name": u.display_name, "role": u.role})