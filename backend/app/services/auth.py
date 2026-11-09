"""认证服务：JWT 生成/校验、密码、令牌。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.security import generate_token


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


def create_refresh_token() -> str:
    return generate_token()


def issue_tokens(user_id: uuid.UUID, role: str) -> dict:
    return {
        "access_token": create_access_token(user_id, role),
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl_minutes * 60,
        "refresh_token": create_refresh_token(),
    }