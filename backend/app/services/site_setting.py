"""网站设置服务：读写 SiteSetting、公开配置聚合。

设计：
- 所有配置以 key → value_json 形式存入 site_settings 表。
- 公开内容仅限 is_public=True 的记录，由 /site/* 公开端点输出。
- 敏感密钥不入此表，一律走环境变量 / Secret 管理。
- 典型 key：public_config / footer / legal / club_intro / announcements。
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import SiteSetting


async def get_setting(db: AsyncSession, key: str) -> dict | None:
    s = (
        await db.scalars(select(SiteSetting).where(SiteSetting.key == key).limit(1))
    ).first()
    return s.value_json if s else None


async def get_public_setting(db: AsyncSession, key: str) -> dict | None:
    s = (
        await db.scalars(
            select(SiteSetting)
            .where(SiteSetting.key == key, SiteSetting.is_public.is_(True))
            .limit(1)
        )
    ).first()
    return s.value_json if s else None


async def upsert_setting(
    db: AsyncSession,
    *,
    key: str,
    value: dict,
    category: str | None = None,
    is_public: bool = False,
    updated_by: uuid.UUID | None = None,
) -> dict:
    s = (
        await db.scalars(select(SiteSetting).where(SiteSetting.key == key).limit(1))
    ).first()
    if s is None:
        s = SiteSetting(
            key=key,
            value_json=value,
            category=category,
            is_public=is_public,
            updated_by=updated_by,
        )
        db.add(s)
    else:
        s.value_json = value
        if category is not None:
            s.category = category
        s.is_public = is_public
        s.updated_by = updated_by
    await db.commit()
    await db.refresh(s)
    return {"key": s.key, "value": s.value_json, "category": s.category, "is_public": s.is_public}


async def list_settings(db: AsyncSession) -> list[dict]:
    rows = (await db.scalars(select(SiteSetting).order_by(SiteSetting.category, SiteSetting.key))).all()
    return [
        {
            "key": r.key,
            "value": r.value_json,
            "category": r.category,
            "is_public": r.is_public,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


# ---------- 公开配置聚合 ----------

_DEFAULT_PUBLIC_CONFIG = {
    "site_name": "啫喱小站",
    "site_subtitle": "温暖、可爱、有社群感的同好之家",
    "logo_url": None,
    "favicon_url": None,
    "icp_number": None,
    "police_number": None,
}

_DEFAULT_FOOTER = {
    "links": [
        {"label": "用户协议", "href": "/legal/terms"},
        {"label": "隐私政策", "href": "/legal/privacy"},
        {"label": "版权声明", "href": "/legal/copyright"},
        {"label": "联系我们", "href": "/legal/contact"},
    ],
    "icp_number": None,
    "police_number": None,
    "copyright_owner": "啫喱小站",
}

_DEFAULT_LEGAL = {
    "terms_url": None,
    "privacy_url": None,
    "copyright_notice": None,
    "contact_email": None,
}

_DEFAULT_CLUB_INTRO = {
    "title": "关于我们",
    "content": "",
}


async def get_public_config(db: AsyncSession) -> dict:
    val = await get_public_setting(db, "public_config")
    return {**_DEFAULT_PUBLIC_CONFIG, **(val or {})}


async def get_footer_config(db: AsyncSession) -> dict:
    val = await get_public_setting(db, "footer")
    return {**_DEFAULT_FOOTER, **(val or {})}


async def get_legal_config(db: AsyncSession) -> dict:
    val = await get_public_setting(db, "legal")
    return {**_DEFAULT_LEGAL, **(val or {})}


async def get_club_intro(db: AsyncSession) -> dict:
    val = await get_public_setting(db, "club_intro")
    return {**_DEFAULT_CLUB_INTRO, **(val or {})}
