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
    upload_url: str
    expires_in: int


class UploadCompleteRequest(BaseModel):
    storage_provider: str
    bucket: str
    object_key: str


class ImageOut(BaseModel):
    id: uuid.UUID
    original_name: str | None
    tags: str | None
    width: int | None
    height: int | None
    description: str | None
    moderation_status: str
    is_public: bool
    copyright_owner: str | None
    license_type: str | None