"""图片 / 上传相关 Schema。"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class UploadIntentRequest(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int = Field(gt=0)
    purpose: str = "gallery"  # gallery / profile / schedule


class UploadCompleteRequest(BaseModel):
    bucket: str
    object_key: str
    purpose: str = "gallery"
    original_name: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class ProfileUploadIntentRequest(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int = Field(gt=0)


class ProfileUploadCompleteRequest(BaseModel):
    bucket: str
    object_key: str
    original_name: str | None = None
    description: str | None = None