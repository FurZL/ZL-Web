"""API v1 路由装配。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_settings,
    admin_users,
    auth,
    club,
    events,
    health,
    images,
    pages,
    profile,
    schedule,
    site,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(images.router)
api_router.include_router(profile.router)
api_router.include_router(schedule.router)
api_router.include_router(pages.router)
api_router.include_router(events.router)
api_router.include_router(site.router)
api_router.include_router(club.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_settings.router)