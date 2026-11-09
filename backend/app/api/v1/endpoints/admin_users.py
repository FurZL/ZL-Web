"""管理端：用户审批、角色、状态。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_permission_dep
from app.api.response import ok

router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(require_permission_dep("user.approve"))],
)


@router.get("/")
async def list_users(request: Request):
    return ok({"items": []})


@router.get("/pending")
async def pending_users(request: Request):
    return ok({"items": []})


@router.get("/{user_id}")
async def get_user(user_id: str, request: Request):
    return ok({"id": user_id})


@router.post("/{user_id}/approve")
async def approve_user(user_id: str, request: Request):
    return ok({"message": "approve stub"})


@router.post("/{user_id}/reject")
async def reject_user(user_id: str, request: Request):
    return ok({"message": "reject stub"})


@router.patch("/{user_id}/role")
async def set_role(user_id: str, request: Request):
    return ok({"message": "role stub"})


@router.patch("/{user_id}/status")
async def set_status(user_id: str, request: Request):
    return ok({"message": "status stub"})