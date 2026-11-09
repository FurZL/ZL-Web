"""课表端点：上传、解析任务查询、对比。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.response import ok
from app.schemas.schedule import CompareRequest
from app.services.schedule import compare as compare_service
from app.services.schedule import CourseSlot

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/upload-intent")
async def upload_intent(request: Request, user=Depends(get_current_user)):
    return ok({"message": "upload-intent stub"})


@router.post("/upload-complete")
async def upload_complete(request: Request, user=Depends(get_current_user)):
    # 解析任务应异步执行，返回 job_id 供前端轮询
    return ok({"job_id": str(uuid.uuid4()), "status": "queued"})


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request, user=Depends(get_current_user)):
    return ok({"job_id": job_id, "status": "pending"})


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str, request: Request):
    return ok({"id": schedule_id})


@router.post("/compare")
async def compare(body: CompareRequest, request: Request):
    slots_a = [
        CourseSlot(**s.model_dump()) for s in body.slots_a
    ]
    slots_b = [
        CourseSlot(**s.model_dump()) for s in body.slots_b
    ]
    return ok(compare_service(slots_a, slots_b))


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, request: Request, user=Depends(get_current_user)):
    return ok({"message": "delete stub"})