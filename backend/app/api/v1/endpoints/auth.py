"""认证端点。

注册：校验邮箱 + 手机验证码 → 创建 pending 用户 → 等待审批。
登录：查库校验 → 签发 Access + Refresh 令牌。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import error_to_http, ok
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    OtpRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.services import auth as auth_service
from app.services.auth import AuthError
from app.core.security import hash_password
from app.services.otp import OtpError, send_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/verify/email")
async def send_email_code(body: OtpRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await send_otp(db, target=body.target, purpose=body.purpose)
    except Exception:
        raise HTTPException(status_code=500, detail={"code": "SEND_FAILED", "message": "验证码发送失败"})
    return ok(result)


@router.post("/verify/phone")
async def send_phone_code(body: OtpRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await send_otp(db, target=body.target, purpose=body.purpose)
    except Exception:
        raise HTTPException(status_code=500, detail={"code": "SEND_FAILED", "message": "验证码发送失败"})
    return ok(result)


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 校验邮箱验证码
    try:
        await verify_otp(db, target=body.email, purpose="register", code=body.email_code)
    except OtpError as exc:
        raise error_to_http(exc)

    # 校验手机验证码
    try:
        await verify_otp(db, target=body.phone, purpose="register", code=body.phone_code)
    except OtpError as exc:
        raise error_to_http(exc)

    try:
        user = await auth_service.register_user(
            db,
            username=body.username,
            display_name=body.display_name,
            email=body.email,
            phone=body.phone,
            password=body.password,
            applied_role=body.applied_role,
            application_reason=body.application_reason,
            application_portfolio=body.application_portfolio,
        )
    except AuthError as exc:
        raise error_to_http(exc)

    return ok({"status": "pending", "message": "注册成功，等待管理员审批"})


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await auth_service.login(
            db,
            account=body.account,
            password=body.password,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await auth_service.refresh_tokens(db, body.refresh_token)
    except AuthError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/logout")
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.revoke_session(db, body.refresh_token)
    return ok({"message": "已退出登录"})


@router.post("/logout-all")
async def logout_all(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await auth_service.revoke_all_sessions(db, user.id)
    return ok({"message": "已退出所有设备"})


@router.post("/password/forgot")
async def forgot_password(body: PasswordForgotRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await send_otp(db, target=body.target, purpose="reset")
    except Exception:
        raise HTTPException(status_code=500, detail={"code": "SEND_FAILED", "message": "验证码发送失败"})
    return ok(result)


@router.post("/password/reset")
async def reset_password(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    try:
        await verify_otp(db, target=body.target, purpose="reset", code=body.code)
    except OtpError as exc:
        raise error_to_http(exc)

    # 找到目标用户并更新密码

    account = body.target.strip()
    query = select(User).where(
        (User.username == account) | (User.email == account) | (User.phone_e164 == account)
    )
    user = (await db.scalars(query.limit(1))).first()
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})

    user.hashed_password = hash_password(body.new_password)
    await db.commit()

    # 撤销全部会话（强制所有设备重新登录）
    await auth_service.revoke_all_sessions(db, user.id)

    return ok({"message": "密码已重置，请使用新密码登录"})


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
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