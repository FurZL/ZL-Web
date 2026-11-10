"""管理端：用户审批、角色、状态。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import UserOut
from app.services import auth as auth_service
from app.services.auth import AuthError

router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(require_permission_dep("user.approve"))],
)

ALLOWED_ROLES = {"member", "photographer", "moderator", "admin"}
ALLOWED_STATUSES = {"active", "disabled"}


def _parse_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "无效的用户 ID"})


@router.get("/")
async def list_users(db: AsyncSession = Depends(get_db)):
    users = (await db.scalars(select(User).order_by(User.created_at.desc()))).all()
    return ok({"items": [UserOut.model_validate(u).model_dump(mode="json") for u in users]})


@router.get("/pending")
async def pending_users(db: AsyncSession = Depends(get_db)):
    users = (
        await db.scalars(
            select(User).where(User.status == "pending").order_by(User.created_at.asc())
        )
    ).all()
    return ok({"items": [UserOut.model_validate(u).model_dump(mode="json") for u in users]})


@router.get("/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, _parse_uuid(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "用户不存在"})
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.post("/{user_id}/approve")
async def approve_user(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.approve_user(db, _parse_uuid(user_id))
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.post("/{user_id}/reject")
async def reject_user(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.reject_user(db, _parse_uuid(user_id))
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


class RolePatchRequest(BaseModel):
    role: str = Field(pattern="^(member|photographer|moderator|admin|super_admin)$")


class StatusPatchRequest(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")


@router.patch("/{user_id}/role")
async def set_role(
    user_id: str,
    body: RolePatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, _parse_uuid(user_id))
    if target is None:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "用户不存在"})

    # 不能修改自己（防止误操作锁定自己）
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail={"code": "SELF_CHANGE", "message": "不能修改自己的角色"})

    # 只有 super_admin 能授予 admin/super_admin
    if body.role in ("admin", "super_admin") and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "只有超级管理员可以授予管理员角色"})

    target.role = body.role
    await db.commit()
    await db.refresh(target)
    return ok(UserOut.model_validate(target).model_dump(mode="json"))


@router.patch("/{user_id}/status")
async def set_status(
    user_id: str,
    body: StatusPatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, _parse_uuid(user_id))
    if target is None:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "用户不存在"})

    # 不能禁用自己
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail={"code": "SELF_CHANGE", "message": "不能修改自己的状态"})

    # 不能禁用 super_admin
    if target.role == "super_admin" and body.status == "disabled":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "不能禁用超级管理员"})

    target.status = body.status
    target.is_active = body.status == "active"

    # 禁用时撤销全部会话（强制下线）
    if body.status == "disabled":
        await auth_service.revoke_all_sessions(db, target.id)
    else:
        await db.commit()

    await db.refresh(target)
    return ok(UserOut.model_validate(target).model_dump(mode="json"))