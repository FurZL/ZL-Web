"""课表端点：上传、解析、查询、对比、删除。

上传走预签名直传；upload-complete 时后端下载文件并解析（ICS/TXT）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import error_to_http, ok, parse_uuid
from app.core.database import get_db
from app.models.user import User
from app.schemas.schedule import (
    AppointmentChoicesRequest,
    AppointmentConfirmRequest,
    AppointmentCreateRequest,
    AppointmentResponseRequest,
    CalendarEventInput,
    CompareRequest,
    FixedAppointmentCreateRequest,
    ScheduleCreateRequest,
    ScheduleMetaRequest,
    ScheduleOrderRequest,
    ScheduleSlotsRequest,
    ScheduleTimingRequest,
    ScheduleUploadCompleteRequest,
    ScheduleUploadIntentRequest,
    ScheduleVisibilityRequest,
)
from app.services import schedule_appointment as schedule_appointment_service
from app.services import schedule_service
from app.services.image import ImageError
from app.services.schedule import CourseSlot
from app.services.schedule import compare as compare_service
from app.services.schedule_appointment import AppointmentError
from app.services.schedule_pdf import MAX_PDF_BYTES, PdfParseError, parse_pdf_schedule
from app.services.schedule_config import require_schedule_feature

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/mine")
async def my_schedules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await schedule_service.get_my_schedules(db, user)
    return ok(result)


@router.put("/order")
async def reorder_schedules(
    body: ScheduleOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """课表架拖动排序：提交本人全部课表的完整顺序。"""
    try:
        result = await schedule_service.reorder_schedules(db, user, body)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/upload-intent")
async def upload_intent(
    body: ScheduleUploadIntentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_schedule_feature(db, "file_import_enabled")
    try:
        intent = await schedule_service.create_schedule_upload_intent(
            user=user, filename=body.filename, size_bytes=body.size_bytes
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(intent)


@router.post("/pdf-preview")
async def preview_pdf(
    file: UploadFile = File(...),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """解析教务 PDF 课表并返回预览；原始 PDF 只在内存中读取，不落库、不写对象存储。"""
    await require_schedule_feature(db, "file_import_enabled")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise error_to_http(ImageError("PDF_TOO_LARGE", "PDF 文件不能超过 10 MB", 422))
    try:
        result = parse_pdf_schedule(data)
    except PdfParseError as exc:
        raise error_to_http(ImageError(exc.code, exc.message, 422))
    return ok(
        {
            "suggested_name": result.suggested_name,
            "slots": [slot.to_dict() for slot in result.slots],
            "warnings": result.warnings,
        }
    )


@router.post("/manual", status_code=201)
async def create_manual_schedule(
    body: ScheduleCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_service.create_manual_schedule(db, user, body)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.get("/calendar")
async def list_calendar(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ok(await schedule_appointment_service.my_events(db, user))


async def _edit_event(db, user, event_id, body):
    try:
        return ok(await schedule_appointment_service.edit_event(db, user, event_id, body))
    except AppointmentError as exc:
        raise error_to_http(exc)


@router.post("/calendar", status_code=201)
async def create_event(
    body: CalendarEventInput,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _edit_event(db, user, None, body)


@router.put("/calendar/{event_id}")
async def edit_event(
    event_id: str,
    body: CalendarEventInput,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _edit_event(db, user, parse_uuid(event_id), body)


@router.delete("/calendar/{event_id}")
async def delete_event(
    event_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _edit_event(db, user, parse_uuid(event_id), None)


@router.get("/appointments")
async def list_appointments(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return ok(await schedule_appointment_service.list_appointments(db, user))


@router.post("/appointments", status_code=201)
async def create_appointment(
    body: AppointmentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_appointment_service.create_appointment(db, user, body)
    except AppointmentError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/appointments/fixed", status_code=201)
async def create_fixed_appointment(
    body: FixedAppointmentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_schedule_feature(db, "fixed_invite_enabled")
    try:
        result = await schedule_appointment_service.create_fixed_appointment(db, user, body)
    except AppointmentError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.get("/meal-notices")
async def meal_notices(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ok(await schedule_appointment_service.notice_count(db, user))


@router.post("/appointments/{appointment_id}/read")
async def mark_meal_read(
    appointment_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    try:
        return ok(
            await schedule_appointment_service.acknowledge(db, parse_uuid(appointment_id), user)
        )
    except AppointmentError as exc:
        raise error_to_http(exc)


@router.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_appointment_service.get_appointment_detail(
            db, parse_uuid(appointment_id, "预约 ID"), user
        )
    except AppointmentError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/appointments/{appointment_id}/response")
async def respond_appointment(
    appointment_id: str,
    body: AppointmentResponseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_appointment_service.respond(
            db, parse_uuid(appointment_id, "预约 ID"), user, body
        )
    except AppointmentError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/appointments/{appointment_id}/choices")
async def choose_appointment_times(
    appointment_id: str,
    body: AppointmentChoicesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_appointment_service.choose(
            db, parse_uuid(appointment_id, "预约 ID"), user, body
        )
    except AppointmentError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/appointments/{appointment_id}/confirm")
async def confirm_appointment(
    appointment_id: str,
    body: AppointmentConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_appointment_service.confirm(
            db, parse_uuid(appointment_id, "预约 ID"), user, body
        )
    except AppointmentError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_appointment_service.cancel(
            db, parse_uuid(appointment_id, "预约 ID"), user
        )
    except AppointmentError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.put("/{schedule_id}/slots")
async def update_slots(
    schedule_id: str,
    body: ScheduleSlotsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_service.update_schedule_slots(
            db, parse_uuid(schedule_id), user, body
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.put("/{schedule_id}/timing")
async def update_timing(
    schedule_id: str,
    body: ScheduleTimingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_service.update_schedule_timing(
            db, parse_uuid(schedule_id), user, body
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/upload-complete")
async def upload_complete(
    body: ScheduleUploadCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_schedule_feature(db, "file_import_enabled")
    try:
        schedule = await schedule_service.complete_schedule_upload(
            db,
            user=user,
            object_key=body.object_key,
            bucket=body.bucket,
            original_name=body.original_name,
        )
    except ImageError as exc:
        raise error_to_http(exc)
    result = await schedule_service.get_schedule(db, schedule.id, user)
    return ok(result)


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_service.get_schedule(db, parse_uuid(schedule_id), user)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.post("/compare")
async def compare(body: CompareRequest, user: User = Depends(get_current_user)):
    slots_a = [CourseSlot(**s.model_dump()) for s in body.slots_a]
    slots_b = [CourseSlot(**s.model_dump()) for s in body.slots_b]
    return ok(compare_service(slots_a, slots_b, week=body.week))


@router.patch("/{schedule_id}/visibility")
async def set_visibility(
    schedule_id: str,
    body: ScheduleVisibilityRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.is_public:
        await require_schedule_feature(db, "public_share_enabled")
    try:
        result = await schedule_service.set_schedule_visibility(
            db, parse_uuid(schedule_id), body.is_public, user
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.patch("/{schedule_id}")
async def update_schedule_meta(
    schedule_id: str,
    body: ScheduleMetaRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """课表架：重命名课表，或存档到历史 / 从历史恢复。"""
    try:
        result = await schedule_service.update_schedule_meta(
            db, parse_uuid(schedule_id), user, body
        )
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.get("/shared/{username}")
async def shared_schedule(
    username: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按用户名获取对方公开的课表（供对比使用）。"""
    try:
        result = await schedule_service.get_public_schedule_by_username(db, username)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok(result)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await schedule_service.delete_schedule(db, parse_uuid(schedule_id), user)
    except ImageError as exc:
        raise error_to_http(exc)
    return ok({"message": "已删除"})
