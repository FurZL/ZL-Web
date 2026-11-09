"""对象存储与图片模型。

StoredObject 统一记录对象存储元数据；Image 记录业务图片信息。
数据库只存对象 Key，不存固定 CDN 完整 URL。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class StoredObject(TimestampMixin, Base):
    __tablename__ = "stored_objects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(32), default="cos")
    bucket: Mapped[str] = mapped_column(String(128))
    object_key: Mapped[str] = mapped_column(String(1024), index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")  # public/private
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending/processing/ready/failed
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Image(TimestampMixin, Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stored_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # 逗号分隔
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderation_status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending/approved/rejected
    is_public: Mapped[bool] = mapped_column(default=False)
    copyright_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    license_type: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ProfileImage(Base):
    """个人空间私有图片（默认私有，仅本人可见）。"""

    __tablename__ = "profile_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    stored_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )