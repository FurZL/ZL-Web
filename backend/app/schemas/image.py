"""图片 / 上传相关 Schema。"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class UploadIntentRequest(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int = Field(gt=0)
    purpose: str = "gallery"  # gallery / profile / schedule


class UploadIntentResponse(BaseModel):
    storage_provider: str
    bucket: str
    object_key: str
    visibility: str
    upload_url: str
    expires_in: int


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


class ImageOut(BaseModel):
    id: str
    url: str | None
    object_key: str | None
    original_name: str | None
    title: str
    description: str | None
    tags: list[str]
    photographer: str
    moderation_status: str
    is_public: bool
    width: int | None
    height: int | None
    uploaded_at: str | None