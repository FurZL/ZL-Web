"""第三方登录（QQ）业务服务。"""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis
from app.core.security import hash_token
from app.models.third_party import UserThirdParty
from app.models.user import User, UserSession
from app.providers.qq import QqOAuthError, QqOAuthProvider
from app.services import auth as auth_service

OAUTH_STATE_TTL_SECONDS = 600
OAUTH_PENDING_TTL_SECONDS = 600
SUPPORTED_PROVIDERS = {"qq"}


def _state_key(token: str) -> str:
    return f"oauth:state:{token}"


def _pending_key(token: str) -> str:
    return f"oauth:pending:{token}"


def _new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def _now() -> datetime:
    return datetime.now(UTC)


def _expires_at(seconds: str | int | None) -> datetime | None:
    if seconds is None:
        return None
    try:
        return _now() + timedelta(seconds=int(seconds))
    except (TypeError, ValueError):
        return None


async def _save_oauth_state(state: str, payload: dict) -> None:
    await redis.set(
        _state_key(state),
        json.dumps(payload, ensure_ascii=False),
        ex=OAUTH_STATE_TTL_SECONDS,
    )


async def take_oauth_state(state: str) -> dict | None:
    raw = await redis.get(_state_key(state))
    if not raw:
        return None
    await redis.delete(_state_key(state))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def save_pending_oauth(
    token: str,
    *,
    provider: str,
    provider_user_id: str,
    unionid: str | None,
    nickname: str,
    avatar_url: str | None,
    return_to: str | None = None,
) -> None:
    await redis.set(
        _pending_key(token),
        json.dumps(
            {
                "provider": provider,
                "provider_user_id": provider_user_id,
                "unionid": unionid,
                "nickname": nickname,
                "avatar_url": avatar_url,
                "return_to": return_to,
            },
            ensure_ascii=False,
        ),
        ex=OAUTH_PENDING_TTL_SECONDS,
    )


async def take_pending_oauth(token: str) -> dict | None:
    raw = await redis.get(_pending_key(token))
    if not raw:
        return None
    await redis.delete(_pending_key(token))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def build_authorize_url(
    provider: str,
    *,
    mode: str = "login",
    user: User | None = None,
    return_to: str | None = None,
) -> str:
    if provider != "qq":
        raise QqOAuthError("OAUTH_PROVIDER_UNSUPPORTED", "暂不支持该登录方式", 400)

    provider_instance = QqOAuthProvider()
    if not provider_instance.configured:
        raise QqOAuthError(
            "OAUTH_QQ_UNAVAILABLE",
            "QQ 登录暂未配置",
            status_code=503,
        )

    state = _new_opaque_token()
    payload = {"mode": mode, "provider": provider, "return_to": return_to}
    if user is not None:
        payload["user_id"] = str(user.id)
    await _save_oauth_state(state, payload)
    return provider_instance.build_authorize_url(state)


async def _find_binding(
    db: AsyncSession,
    provider: str,
    provider_user_id: str,
    unionid: str | None,
) -> UserThirdParty | None:
    conditions = [
        and_(
            UserThirdParty.provider == provider,
            UserThirdParty.provider_user_id == provider_user_id,
        )
    ]
    if unionid:
        conditions.append(
            and_(
                UserThirdParty.provider == provider,
                UserThirdParty.unionid == unionid,
            )
        )
    rows = (
        await db.scalars(
            select(UserThirdParty).where(or_(*conditions)).order_by(UserThirdParty.created_at)
        )
    ).all()
    if rows:
        return rows[0]
    return None


async def _issue_tokens(db: AsyncSession, user: User) -> dict:
    access_token = auth_service.create_access_token(user.id, user.role)
    refresh_token = auth_service._create_refresh_token()
    db.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            expires_at=_now() + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    await db.commit()
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl_minutes * 60,
        "refresh_token": refresh_token,
    }


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "avatar_url": auth_service._get_avatar_url(user),
        "bio": user.bio or "",
    }


async def exchange_and_resolve(
    db: AsyncSession,
    *,
    provider: str,
    code: str,
    state: str,
) -> dict:
    state_payload = await take_oauth_state(state)
    if not state_payload or state_payload.get("provider") != provider:
        raise QqOAuthError("OAUTH_STATE_INVALID", "授权状态无效，请重新发起", 400)

    provider_instance = QqOAuthProvider()
    try:
        oauth_profile = await provider_instance.exchange_code(code)
    except QqOAuthError:
        raise

    mode = state_payload.get("mode", "login")
    provider_user_id = oauth_profile["provider_user_id"]
    unionid = oauth_profile.get("unionid")

    if mode == "bind":
        user_id = state_payload.get("user_id")
        if not user_id:
            raise QqOAuthError("OAUTH_BIND_FAILED", "绑定会话无效", 400)
        user = await db.get(User, uuid.UUID(user_id))
        if user is None:
            raise QqOAuthError("OAUTH_USER_NOT_FOUND", "用户不存在", 404)

        existing = await _find_binding(db, provider, provider_user_id, unionid)
        if existing is not None and existing.user_id != user.id:
            raise QqOAuthError(
                "OAUTH_ALREADY_BOUND",
                "该 QQ 已绑定其他账号",
                status_code=409,
            )
        if existing is None:
            token_expires_at = _expires_at(oauth_profile.get("expires_in"))
            db.add(
                UserThirdParty(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=provider_user_id,
                    unionid=unionid,
                    access_token=oauth_profile.get("access_token"),
                    refresh_token=oauth_profile.get("refresh_token"),
                    expires_at=token_expires_at,
                    raw_profile=oauth_profile.get("raw_profile") or {},
                )
            )
        else:
            existing.unionid = unionid
            existing.access_token = oauth_profile.get("access_token")
            existing.refresh_token = oauth_profile.get("refresh_token")
            existing.expires_at = _expires_at(oauth_profile.get("expires_in"))
            existing.raw_profile = oauth_profile.get("raw_profile") or {}
            existing.updated_at = _now()
        await db.commit()
        return {
            "bound": True,
            "provider": provider,
            "user": _user_payload(user),
            "return_to": state_payload.get("return_to"),
        }

    # login 模式：已有绑定则直接登录，未绑定时签发一个短时 oauth_token。
    existing = await _find_binding(db, provider, provider_user_id, unionid)
    if existing is not None:
        user = await db.get(User, existing.user_id)
        if user is None:
            raise QqOAuthError("OAUTH_USER_NOT_FOUND", "绑定的账号不存在", 404)
        if user.status != "active" or not user.is_active:
            if user.status == "pending":
                raise QqOAuthError(
                    "PENDING_APPROVAL",
                    "账号尚未通过审批，请耐心等待",
                    status_code=403,
                )
            raise QqOAuthError("ACCOUNT_DISABLED", "账号已被禁用", 403)
        user.last_login_at = _now()
        tokens = await _issue_tokens(db, user)
        return {
            "bound": True,
            "user": _user_payload(user),
            **tokens,
        }

    oauth_token = _new_opaque_token()
    await save_pending_oauth(
        oauth_token,
        provider=provider,
        provider_user_id=provider_user_id,
        unionid=unionid,
        nickname=oauth_profile["nickname"],
        avatar_url=oauth_profile.get("avatar_url"),
        return_to=state_payload.get("return_to"),
    )
    return {
        "bound": False,
        "oauth_token": oauth_token,
        "provider": provider,
        "nickname": oauth_profile["nickname"],
        "return_to": state_payload.get("return_to"),
    }


async def bind_with_credentials(
    db: AsyncSession,
    *,
    oauth_token: str,
    account: str,
    password: str,
) -> dict:
    pending = await take_pending_oauth(oauth_token)
    if not pending:
        raise QqOAuthError("OAUTH_PENDING_EXPIRED", "授权已过期，请重新发起", 400)

    user = await auth_service._find_by_account(db, account)
    if user is None or not auth_service.verify_password(password, user.hashed_password):
        raise QqOAuthError("INVALID_CREDENTIALS", "用户名或密码错误", 401)
    if user.status != "active" or not user.is_active:
        if user.status == "pending":
            raise QqOAuthError(
                "PENDING_APPROVAL",
                "账号尚未通过审批，请耐心等待",
                status_code=403,
            )
        raise QqOAuthError("ACCOUNT_DISABLED", "账号已被禁用", 403)

    existing = await _find_binding(
        db,
        pending["provider"],
        pending["provider_user_id"],
        pending.get("unionid"),
    )
    if existing is not None and existing.user_id != user.id:
        raise QqOAuthError(
            "OAUTH_ALREADY_BOUND",
            "该 QQ 已绑定其他账号",
            status_code=409,
        )
    if existing is None:
        db.add(
            UserThirdParty(
                user_id=user.id,
                provider=pending["provider"],
                provider_user_id=pending["provider_user_id"],
                unionid=pending.get("unionid"),
                raw_profile={},
            )
        )
        await db.commit()

    user.last_login_at = _now()
    tokens = await _issue_tokens(db, user)
    return {
        "bound": True,
        "user": _user_payload(user),
        "return_to": pending.get("return_to"),
        **tokens,
    }


async def list_bindings(db: AsyncSession, user: User) -> list[dict]:
    rows = (
        await db.scalars(
            select(UserThirdParty)
            .where(UserThirdParty.user_id == user.id)
            .order_by(UserThirdParty.created_at)
        )
    ).all()
    return [
        {
            "provider": row.provider,
            "provider_user_id": row.provider_user_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


async def unbind_provider(db: AsyncSession, user: User, provider: str) -> None:
    rows = (
        await db.scalars(
            select(UserThirdParty).where(
                UserThirdParty.user_id == user.id,
                UserThirdParty.provider == provider,
            )
        )
    ).all()
    for row in rows:
        await db.delete(row)
    await db.commit()


async def is_oauth_public_enabled(db: AsyncSession, provider: str | None = None) -> bool:
    from app.services import site_setting

    cfg = await site_setting.get_oauth_config(db)
    if not cfg.get("enabled", False):
        return False
    if provider and provider not in SUPPORTED_PROVIDERS:
        return False
    key = f"{provider}_enabled"
    return bool(cfg.get(key, False))

