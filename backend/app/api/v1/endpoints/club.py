"""社团介绍端点。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission_dep
from app.api.response import ok
from app.core.database import get_db
from app.models.user import User
from app.services import site_setting

router = APIRouter(prefix="/club", tags=["club"])


class ClubIntroUpdate(BaseModel):
    title: str = "关于我们"
    content: str


@router.get("/intro")
async def get_intro(db: AsyncSession = Depends(get_db)):
    return ok(await site_setting.get_club_intro(db))


@router.put("/intro")
async def update_intro(
    body: ClubIntroUpdate,
    user: User = Depends(require_permission_dep("site_config.manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await site_setting.upsert_setting(
        db,
        key="club_intro",
        value={"title": body.title, "content": body.content},
        category="club",
        is_public=True,
        updated_by=user.id,
    )
    return ok(result)
