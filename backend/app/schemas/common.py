"""通用响应结构。

统一 JSON 响应：{"success":…, "data":…, "error":…, "request_id":…}
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None
    request_id: str | None = None


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    items: list[T] = []
    pagination: Pagination