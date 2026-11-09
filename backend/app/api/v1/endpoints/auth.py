"""认证端点。

注册：校验邮箱 + 手机验证码 → 创建 pending 用户 → 等待审批。
登录：查库校验 → 签发 Access + Refresh 令牌。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import ok
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    OtpRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    UserOut,
)
from app.services import auth as auth_service
from app.services.auth import AuthError
from app.services.otp import OtpError, send_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_error(exc: AuthError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _otp_error(exc: OtpError) -> HTTPException:
    return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})


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
        raise _otp_error(exc)

    # 校验手机验证码
    try:
        await verify_otp(db, target=body.phone, purpose="register", code=body.phone_code)
    except OtpError as exc:
        raise _otp_error(exc)

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
        raise _auth_error(exc)

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
        raise _auth_error(exc)
    return ok(result)


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await auth_service.refresh_tokens(db, body.refresh_token)
    except AuthError as exc:
        raise _auth_error(exc)
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
        raise _otp_error(exc)
    # TODO: 更新密码（此阶段可先占位）
    return ok({"message": "密码已重置"})


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user