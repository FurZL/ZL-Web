"""统一响应辅助。"""

from __future__ import annotations

from fastapi import Request


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