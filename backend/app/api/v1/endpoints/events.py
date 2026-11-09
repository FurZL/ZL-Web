"""活动与公告端点。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.response import ok

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/")
async def list_events(request: Request):
    return ok({"items": []})


@router.get("/{event_id}")
async def get_event(event_id: str, request: Request):
    return ok({"id": event_id})


@router.post("/{event_id}/register")
async def register_event(event_id: str, request: Request, user=Depends(get_current_user)):
    return ok({"message": "register stub"})


@router.delete("/{event_id}/register")
async def cancel_registration(event_id: str, request: Request, user=Depends(get_current_user)):
    return ok({"message": "cancel stub"})


@router.post("/{event_id}/checkin")
async def checkin(event_id: str, request: Request, user=Depends(get_current_user)):
    return ok({"message": "checkin stub"})