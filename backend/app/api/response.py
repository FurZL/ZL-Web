"""统一响应辅助。"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, Request


def ok(data=None, request: Request | None = None) -> dict:
    request_id = getattr(request, "state", None)
    request_id = getattr(request_id, "request_id", None) if request_id else None
    return {
        "success": True,
        "data": data,
        "error": None,
        "request_id": request_id,
    }


def err(code: str, message: str, request: Request | None = None) -> dict:
    request_id = getattr(request, "state", None)
    request_id = getattr(request_id, "request_id", None) if request_id else None
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "request_id": request_id,
    }


def parse_uuid(value: str, field: str = "ID") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_ID", "message": f"无效的{field}"},
        )


def error_to_http(exc) -> HTTPException:
    """把 ServiceError 转换为 HTTPException。

    适用于所有带 code/message/status_code 属性的 ServiceError
    （ImageError / EventError / PageError / AuthError 等）。
    """
    return HTTPException(
        status_code=getattr(exc, "status_code", 400),
        detail={"code": exc.code, "message": exc.message},
    )