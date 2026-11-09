"""API 依赖：认证、当前用户、权限、数据库会话等。"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.services.auth import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """从 Bearer Token 解析当前用户（轻量，不强制查库；需要时可扩展查询）。"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "未登录"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "令牌无效或已过期"},
        )
    user_id = uuid.UUID(payload["sub"])
    role = payload.get("role", "member")
    return {"id": user_id, "role": role}


def require_role(*roles: str):
    async def _dep(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "权限不足"},
            )
        return user

    return _dep


def require_permission_dep(permission: str):
    async def _dep(user=Depends(get_current_user)):
        try:
            require_permission(user["role"], permission)
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": f"缺少权限: {permission}"},
            )
        return user

    return _dep