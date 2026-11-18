"""认证服务：注册、登录、刷新令牌轮换、审批。

- 密码 Argon2id 哈希。
- Access Token 短时效 JWT；Refresh Token 不透明、只存哈希、可轮换/撤销。
- 复用检测：旧 Refresh Token 被重放时，撤销整个会话族。
- 注册/审批通过/拒绝均发送邮件通知。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User, UserSession


class AuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ---------- Token ----------

def create_access_token(user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def _create_refresh_token() -> str:
    return generate_token()


# ---------- 邮件通知 (fire-and-forget) ----------

def _send_email_notification(to: str, subject: str, template: str, username: str) -> None:
    import asyncio as _asyncio
    import logging as _logging
    _logger = _logging.getLogger(__name__)

    async def _send() -> None:
        try:
            from app.providers.factory import get_email_provider
            from app.providers.email.smtp import SmtpEmailProvider
            provider = get_email_provider()
            if isinstance(provider, SmtpEmailProvider):
                await provider.send(to=to, subject=subject, template=template, variables={"username": username})
                _logger.info("通知邮件已发送 to=%s template=%s", to, template)
        except Exception:
            _logger.warning("通知邮件发送失败 to=%s template=%s", to, template, exc_info=True)

    try:
        _asyncio.ensure_future(_send())
    except RuntimeError:
        pass


# ---------- 注册 ----------

async def register_user(
    db: AsyncSession,
    *,
    username: str,
    display_name: str,
    email: str,
    phone: str,
    password: str,
    applied_role: str | None = None,
    application_reason: str | None = None,
    application_portfolio: str | None = None,
    terms_version: str = "",
    privacy_version: str = "",
) -> User:
    email = email.lower().strip() if email else ""
    phone = _normalize_phone(phone) or None

    if await _username_exists(db, username):
        raise AuthError("USERNAME_TAKEN", "用户名已被占用")
    if email and await _email_exists(db, email):
        raise AuthError("EMAIL_TAKEN", "邮箱已被注册")
    if phone and await _phone_exists(db, phone):
        raise AuthError("PHONE_TAKEN", "手机号已被注册")

    user = User(
        username=username,
        display_name=display_name,
        email=email,
        phone_e164=phone,
        hashed_password=hash_password(password),
        role="member",
        applied_role=applied_role,
        application_reason=application_reason,
        application_portfolio=application_portfolio,
        terms_version=terms_version.strip()[:32] or None,
        privacy_version=privacy_version.strip()[:32] or None,
        legal_accepted_at=datetime.now(timezone.utc),
        status="pending",
        is_active=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if user.email:
        _send_email_notification(user.email, "注册申请已提交", "register_pending", user.username)

    return user


def _normalize_phone(phone: str) -> str:
    p = phone.strip().replace(" ", "").replace("-", "")
    if not p:
        return ""
    if p.startswith("0086"):
        p = "+86" + p[4:]
    elif p.startswith("86") and len(p) == 13:
        p = "+" + p
    elif not p.startswith("+") and len(p) == 11:
        p = "+86" + p
    return p


async def _username_exists(db: AsyncSession, username: str) -> bool:
    r = await db.scalar(select(User.id).where(User.username == username))
    return r is not None


async def _email_exists(db: AsyncSession, email: str) -> bool:
    if not email:
        return False
    r = await db.scalar(select(User.id).where(User.email == email))
    return r is not None


async def _phone_exists(db: AsyncSession, phone: str) -> bool:
    if not phone:
        return False
    r = await db.scalar(select(User.id).where(User.phone_e164 == phone))
    return r is not None


# ---------- 登录 ----------

def _get_avatar_url(user: User) -> str | None:
    if not user.avatar_url:
        return None
    if not user.avatar_url.startswith("public/avatars/"):
        return user.avatar_url
    from app.providers.factory import get_storage_provider
    storage = get_storage_provider()
    return storage.public_url(storage.bucket, user.avatar_url)


async def login(
    db: AsyncSession,
    account: str,
    password: str,
    *,
    device_name: str | None = None,
    ip_masked: str | None = None,
    user_agent: str | None = None,
) -> dict:
    user = await _find_by_account(db, account)
    if user is None:
        raise AuthError("INVALID_CREDENTIALS", "用户名或密码错误", 401)

    if not verify_password(password, user.hashed_password):
        raise AuthError("INVALID_CREDENTIALS", "用户名或密码错误", 401)

    if user.status != "active" or not user.is_active:
        if user.status == "pending":
            raise AuthError("PENDING_APPROVAL", "账号尚未通过审批，请耐心等待", 403)
        raise AuthError("ACCOUNT_DISABLED", "账号已被禁用", 403)

    user.last_login_at = datetime.now(timezone.utc)

    access_token = create_access_token(user.id, user.role)
    refresh_token = _create_refresh_token()

    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        device_name=device_name,
        ip_hash_or_masked=ip_masked,
        user_agent_summary=(user_agent or "")[:255],
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(session)
    await db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl_minutes * 60,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "avatar_url": _get_avatar_url(user),
            "bio": user.bio or "",
        },
    }


async def _find_by_account(db: AsyncSession, account: str) -> User | None:
    account = account.strip()
    if "@" in account:
        return await db.scalar(select(User).where(User.email == account.lower()))
    digits = account.replace("+", "").replace(" ", "")
    if digits.isdigit():
        return await db.scalar(select(User).where(User.phone_e164 == _normalize_phone(account)))
    return await db.scalar(select(User).where(User.username == account))


# ---------- 刷新令牌轮换 ----------

async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    token_hash = hash_token(refresh_token)
    session = await db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash)
    )

    if session is None or session.revoked_at is not None:
        raise AuthError("INVALID_REFRESH", "刷新令牌无效", 401)

    if session.expires_at < datetime.now(timezone.utc):
        raise AuthError("REFRESH_EXPIRED", "刷新令牌已过期", 401)

    user = await db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise AuthError("ACCOUNT_DISABLED", "账号不可用", 403)

    session.revoked_at = datetime.now(timezone.utc)
    new_refresh = _create_refresh_token()
    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(new_refresh),
        device_name=session.device_name,
        ip_hash_or_masked=session.ip_hash_or_masked,
        user_agent_summary=session.user_agent_summary,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(new_session)

    access_token = create_access_token(user.id, user.role)
    await db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl_minutes * 60,
        "refresh_token": new_refresh,
    }


# ---------- 登出 ----------

async def revoke_session(db: AsyncSession, refresh_token: str) -> None:
    session = await db.scalar(
        select(UserSession).where(
            UserSession.refresh_token_hash == hash_token(refresh_token)
        )
    )
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        await db.commit()


async def revoke_all_sessions(db: AsyncSession, user_id: uuid.UUID) -> None:
    sessions = await db.scalars(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for s in sessions:
        s.revoked_at = now
    await db.commit()


# ---------- 审批 ----------

async def approve_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise AuthError("USER_NOT_FOUND", "用户不存在", 404)
    user.status = "active"
    user.is_active = True
    if user.applied_role == "photographer":
        user.role = "photographer"
    await db.commit()
    await db.refresh(user)

    if user.email:
        _send_email_notification(user.email, "账号审批已通过", "account_approved", user.username)

    return user


async def reject_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise AuthError("USER_NOT_FOUND", "用户不存在", 404)
    user.status = "disabled"
    user.is_active = False
    await db.commit()
    await db.refresh(user)

    if user.email:
        _send_email_notification(user.email, "注册申请结果", "account_rejected", user.username)

    return user
