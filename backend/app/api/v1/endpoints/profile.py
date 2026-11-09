"""个人空间端点。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.response import ok

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me")
async def get_me(request: Request, user=Depends(get_current_user)):
    return ok({"id": str(user["id"]), "role": user["role"]})


@router.put("/me")
async def update_me(request: Request, user=Depends(get_current_user)):
    return ok({"message": "update stub"})


@router.get("/me/images")
async def my_images(request: Request, user=Depends(get_current_user)):
    return ok({"items": []})


@router.post("/me/images/upload-intent")
async def upload_intent(request: Request, user=Depends(get_current_user)):
    return ok({"message": "upload-intent stub"})


@router.delete("/me/images/{image_id}")
async def delete_image(image_id: str, request: Request, user=Depends(get_current_user)):
    return ok({"message": "delete stub"})


@router.get("/{user_id}")
async def public_profile(user_id: str, request: Request):
    return ok({"id": user_id})