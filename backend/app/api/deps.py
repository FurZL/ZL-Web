"""API 依赖：认证、当前用户、权限、数据库会话等。"""

from __future__ import annotations

import time
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.redis import redis
from app.models.user import User
from app.services.auth import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Bearer Token 解析并查库返回真实用户。

    权限最终以数据库中的 role/status 为准（不信任 JWT 中的陈旧 role）。
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "未登录"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "令牌无效或已过期"},
        )

    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "账号不可用"},
        )
    return user


def require_role(*roles: str):
    async def _dep(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "权限不足"},
            )
        return user

    return _dep


def require_permission_dep(permission: str):
    async def _dep(user: User = Depends(get_current_user)):
        try:
            require_permission(user.role, permission)
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": f"缺少权限: {permission}"},
            )
        return user

    return _dep


def rate_limit(scope: str, limit: int, window_seconds: int):
    """基于 Redis 固定窗口的轻量应用层限流（作为 WAF/网关之外的第二道闸）。"""

    async def _dep(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        bucket = int(time.time() // window_seconds)
        key = f"ratelimit:{scope}:{client_ip}:{bucket}"
        try:
            async with redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window_seconds * 2)
                count, _ = await pipe.execute()
        except Exception:
            # Redis 故障时失败开放，避免把正常用户一起挡在门外；由网关联限流兜底
            return
        if int(count) > limit:
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "请求过于频繁，请稍后再试"},
                headers={"Retry-After": str(window_seconds)},
            )

    return _dep
