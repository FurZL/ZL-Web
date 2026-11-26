"""Calculate group availability and issue fixed-time invitations."""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from app.models.schedule import Schedule
from app.models.schedule_appointment import CalendarEvent, ScheduleAppointment, ScheduleAppointmentParticipant
from app.models.schedule_group import ScheduleGroupMember
from app.models.user import User
from app.schemas.schedule import MealWindow
from app.services.image import ImageError
from app.services.meal_times import CAMPUS, DAY, MINUTE, available, busy_intervals
from app.services.schedule_appointment import check_calendar, detail, lock_owners, now
from app.services.schedule_group import _active_member, _group
from app.services.schedule_timing import timing_to_calendar


async def availability(db, user, group_id, body):
    await _group(db, group_id)
    await _active_member(db, group_id, user.id)
    if user.id in body.member_ids:
        raise ImageError("INVALID_MEMBERS", "无需重复选择自己", 422)
    ids = [user.id, *body.member_ids]
    rows = (await db.execute(
        select(ScheduleGroupMember, Schedule, User)
        .join(Schedule, Schedule.id == ScheduleGroupMember.schedule_id)
        .join(User, User.id == ScheduleGroupMember.user_id)
        .where(ScheduleGroupMember.group_id == group_id, ScheduleGroupMember.user_id.in_(ids),
               ScheduleGroupMember.status == "active", Schedule.owner_id == ScheduleGroupMember.user_id,
               Schedule.is_archived.is_(False), User.status == "active", User.is_active.is_(True))
    )).all()
    if len(rows) != len(ids):
        raise ImageError("GROUP_SCHEDULE_REQUIRED", "所选成员必须在群内且已共享有效课表", 409)
    calendars = []
    own_calendar = None
    for member, schedule, _ in rows:
        try:
            calendar = timing_to_calendar((schedule.parsed_json or {}).get("timing"))
        except (ValueError, KeyError, TypeError):
            raise ImageError("TIMING_NOT_READY", "所选成员需要先设置学期开始日期和作息", 409)
        slots = (schedule.parsed_json or {}).get("slots", [])
        if any(not 1 <= s.get("lesson_start", 0) <= s.get("lesson_end", 0) <= len(calendar["periods"]) for s in slots):
            raise ImageError("UNKNOWN_PERIOD", "所选课表包含作息范围外的节次", 409)
        calendars.append((slots, calendar))
        if member.user_id == user.id:
            own_calendar = calendar
    first_day = date.fromisoformat(own_calendar["term_start"]) + timedelta(weeks=body.week - 1)
    window = MealWindow(date_from=first_day, date_to=first_day + timedelta(days=6), daily_start="00:00", daily_end="23:59", duration_minutes=15)
    for _, calendar in calendars:
        check_calendar(calendar, window)
    first_instant = datetime.combine(first_day, time.min, CAMPUS)
    events = (await db.scalars(select(CalendarEvent).where(
        CalendarEvent.owner_id.in_(ids), CalendarEvent.ends_at >= first_instant - DAY,
        CalendarEvent.starts_at < first_instant + 8 * DAY,
    ))).all()
    busy = busy_intervals(window, calendars, events)
    current = now()
    slots = []
    for weekday in range(7):
        day = first_day + timedelta(days=weekday)
        for number, (first, last) in enumerate(own_calendar["periods"], start=1):
            start = datetime.combine(day, time.fromisoformat(first), CAMPUS)
            end = datetime.combine(day, time.fromisoformat(last), CAMPUS)
            if end - start >= 15 * MINUTE and available(start, end, busy, 0 * MINUTE, current):
                slots.append({"weekday": weekday, "lesson": number, "starts_at": start.isoformat(), "ends_at": end.isoformat()})
    return {"week": body.week, "member_count": len(ids), "slots": slots}


async def create_invitation(db, user, group_id, body):
    await _group(db, group_id)
    await _active_member(db, group_id, user.id)
    if user.id in body.member_ids:
        raise ImageError("INVALID_MEMBERS", "无需重复选择自己", 422)
    selected_ids = set((await db.scalars(select(ScheduleGroupMember.user_id).where(
        ScheduleGroupMember.group_id == group_id, ScheduleGroupMember.status == "active",
        ScheduleGroupMember.user_id.in_(body.member_ids),
    ))).all())
    if selected_ids != set(body.member_ids):
        raise ImageError("GROUP_SCHEDULE_REQUIRED", "所选成员必须在群内且已共享有效课表", 409)
    await lock_owners(db, [user.id, *body.member_ids])
    result = await availability(db, user, group_id, body)
    slot = next((s for s in result["slots"] if s["weekday"] == body.weekday and s["lesson"] == body.lesson_start), None)
    if slot is None:
        raise ImageError("TIME_BUSY", "共同空闲时间已变化，请重新查询", 409)
    member = await _active_member(db, group_id, user.id)
    schedule = await db.get(Schedule, member.schedule_id)
    calendar = timing_to_calendar((schedule.parsed_json or {}).get("timing"))
    start, end = datetime.fromisoformat(slot["starts_at"]), datetime.fromisoformat(slot["ends_at"])
    existing = (await db.scalars(select(ScheduleAppointment).where(
        ScheduleAppointment.organizer_id == user.id, ScheduleAppointment.status == "pending",
        ScheduleAppointment.expires_at > now(),
    ))).all()
    for old in existing:
        if (old.preferences or {}).get("mode") != "group_fixed" or old.preferences.get("fixed_start") != slot["starts_at"]:
            continue
        old_ids = set((await db.scalars(select(ScheduleAppointmentParticipant.user_id).where(ScheduleAppointmentParticipant.appointment_id == old.id))).all())
        if old_ids == {user.id, *body.member_ids}:
            raise ImageError("INVITATION_EXISTS", "已经向这些成员发出相同时段的邀请", 409)
    window = MealWindow(date_from=start.date(), date_to=start.date(), daily_start=start.strftime("%H:%M"), daily_end=end.strftime("%H:%M"), duration_minutes=int((end - start).total_seconds() // 60))
    preferences = {**window.model_dump(mode="json"), "mode": "group_fixed", "group_id": str(group_id),
                   "fixed_start": slot["starts_at"], "fixed_end": slot["ends_at"], "fixed_week": body.week,
                   "fixed_weekday": body.weekday, "fixed_lesson_start": body.lesson_start, "fixed_lesson_end": body.lesson_start}
    appointment = ScheduleAppointment(organizer_id=user.id, title=body.title, location=body.location,
        status="pending", preferences=preferences, candidates_json=[{"id": "fixed", "starts_at": slot["starts_at"], "ends_at": slot["ends_at"]}], expires_at=min(now() + 3 * DAY, start))
    db.add(appointment)
    await db.flush()
    participants = [ScheduleAppointmentParticipant(appointment_id=appointment.id, user_id=user.id, role="organizer", status="accepted", schedule_id=schedule.id, calendar=calendar)]
    participants.extend(ScheduleAppointmentParticipant(appointment_id=appointment.id, user_id=uid, role="invitee", status="invited", notice="你收到了一个群组时间约定") for uid in body.member_ids)
    db.add_all(participants)
    await db.commit()
    return await detail(db, appointment, participants, participants[0])
