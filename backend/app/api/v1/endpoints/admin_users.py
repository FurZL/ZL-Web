"""管理端：用户审批、角色、状态。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
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


@router.patch("/{user_id}/role")
async def set_role(user_id: str, db: AsyncSession = Depends(get_db)):
    # role 变更通过受控权限调用；逻辑可后续补充
    return ok({"message": "pending"})


@router.patch("/{user_id}/status")
async def set_status(user_id: str, db: AsyncSession = Depends(get_db)):
    return ok({"message": "pending"})