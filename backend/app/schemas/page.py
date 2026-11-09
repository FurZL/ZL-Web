"""动态页面 Schema。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class Theme(BaseModel):
    primary: str | None = None
    background: str | None = None


class PageSchema(BaseModel):
    slug: str | None = None
    title: str | None = None
    theme: Theme | None = None
    blocks: list[dict] = []


class PageCreate(BaseModel):
    slug: str
    title: str
    description: str | None = None
    schema_json: dict
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    seo_title: str | None = None
    seo_description: str | None = None


class PageOut(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    status: str
    schema_json: dict
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    published_at: datetime | None = None