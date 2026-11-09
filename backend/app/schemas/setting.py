"""网站设置 / 公开配置 Schema。"""

from __future__ import annotations

from pydantic import BaseModel


class PublicConfig(BaseModel):
    site_name: str | None = None
    site_subtitle: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    icp_number: str | None = None
    police_number: str | None = None
    footer_html: str | None = None


class SettingUpdate(BaseModel):
    key: str
    value: dict
    category: str | None = None
    is_public: bool = False