"""网站设置模型。

仅公开标记 is_public 的配置可通过公共 API 输出；
敏感密钥一律放 Secret 管理，不进入此表。
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class SiteSetting(TimestampMixin, Base):
    __tablename__ = "site_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)