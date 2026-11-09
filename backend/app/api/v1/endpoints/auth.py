"""认证端点。

注册流程为占位实现：核验 OTP 后创建 pending 用户，管理员审批后激活。
生产需接入真实 Provider 与限流、审计，详见 docs/SECURITY.md。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.api.response import err, ok
from app.schemas.auth import (
    LoginRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    UserOut,
)
from app.services.auth import issue_tokens

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    # TODO: 校验邮箱/手机 OTP、人机验证、创建 pending 用户
    return ok({"status": "pending", "message": "注册请求已提交，等待审批"})


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    # TODO: 查询用户、校验密码、限流、签发令牌
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"},
    )


@router.post("/refresh")
async def refresh(body: RefreshRequest, request: Request):
    # TODO: 校验 refresh_token 哈希、轮换、复用检测
    return ok({"message": "refresh endpoint stub"})


@router.post("/logout")
async def logout(request: Request):
    return ok({"message": "logout stub"})


@router.post("/logout-all")
async def logout_all(request: Request):
    return ok({"message": "logout-all stub"})


@router.post("/password/forgot")
async def forgot_password(request: Request):
    return ok({"message": "forgot stub"})


@router.post("/password/reset")
async def reset_password(body: PasswordResetRequest, request: Request):
    return ok({"message": "reset stub"})


@router.get("/me", response_model=dict)
async def me(user=Depends(get_current_user)):
    return ok({"id": str(user["id"]), "role": user["role"]})