"""一对一邀请、选时、确认和个人日程。所有业务判断都在 API 内完成。"""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, func, select

from app.models.schedule import Schedule
from app.models.schedule_appointment import CalendarEvent
from app.models.schedule_appointment import ScheduleAppointment as Meal
from app.models.schedule_appointment import ScheduleAppointmentParticipant as Member
from app.models.user import User
from app.schemas.schedule import FixedAppointmentCreateRequest, MealWindow
from app.services.image import ImageError
from app.services.meal_times import CAMPUS, DAY, MINUTE, available, busy_intervals, recommend
from app.services.schedule_timing import timing_to_calendar


class AppointmentError(ImageError):
    pass


def now():
    return datetime.now(UTC)


def state(meal):
    if meal.status in {"pending", "choosing", "confirming"} and meal.expires_at <= now():
        return "expired"
    return meal.status


async def owned(db, schedule_id, owner_id, lock=False):
    q = select(Schedule).where(Schedule.id == schedule_id, Schedule.owner_id == owner_id)
    if lock:
        q = q.with_for_update().execution_options(populate_existing=True)
    row = await db.scalar(q)
    if not row:
        raise AppointmentError("SCHEDULE_NOT_FOUND", "参与课表不存在，请重新选择课表发起邀请", 409)
    return row


def check_calendar(calendar, window):
    anchor = date.fromisoformat(calendar["term_start"])
    if window.date_from < anchor or (window.date_to - anchor).days >= 371:
        raise AppointmentError("INVALID_TERM", "可约日期必须在该课表第 1–53 周内", 400)


async def access(db, mid, uid, lock=True):
    q = select(Meal).where(
        Meal.id == mid, Meal.id.in_(select(Member.appointment_id).where(Member.user_id == uid))
    )
    if lock:
        q = q.with_for_update().execution_options(populate_existing=True)
    meal = await db.scalar(q)
    if not meal:
        raise AppointmentError("NOT_FOUND", "约饭不存在", 404)
    members = list(
        (
            await db.scalars(
                select(Member)
                .where(Member.appointment_id == mid)
                .order_by(Member.user_id)
                .execution_options(populate_existing=True)
            )
        ).all()
    )
    return meal, members, next(p for p in members if p.user_id == uid)


def common_ids(members):
    if not all(p.status == "accepted" for p in members):
        return set()
    return set.intersection(*(set(p.choices_json or []) for p in members))


async def detail(db, meal, members, viewer, names=None):
    if names is None:
        names = dict(
            (
                await db.execute(
                    select(User.id, User.username).where(User.id.in_([m.user_id for m in members]))
                )
            ).all()
        )
    mode = (meal.preferences or {}).get("mode", "meal")
    fixed = None
    if mode in {"fixed", "group_fixed"}:
        fixed = {
            "starts_at": meal.preferences.get("fixed_start"),
            "ends_at": meal.preferences.get("fixed_end"),
            "week": meal.preferences.get("fixed_week"),
            "weekday": meal.preferences.get("fixed_weekday"),
            "lesson_start": meal.preferences.get("fixed_lesson_start"),
            "lesson_end": meal.preferences.get("fixed_lesson_end"),
        }
    return {
        "id": str(meal.id),
        "title": meal.title,
        "location": meal.location,
        "mode": "fixed" if mode == "group_fixed" else mode,
        "is_group": mode == "group_fixed",
        "fixed": fixed,
        "window": meal.preferences,
        "status": state(meal),
        "candidates": meal.candidates_json,
        "selected_candidate_id": meal.selected_candidate_id,
        "common_candidate_ids": sorted(common_ids(members)),
        "expires_at": meal.expires_at.isoformat(),
        "notice": viewer.notice,
        "viewer_participant": {
            "role": viewer.role,
            "status": viewer.status,
            "choices": viewer.choices_json,
            "confirmed_candidate_id": viewer.confirmed_candidate_id,
        },
        "participants": [
            {
                "username": names[m.user_id],
                "role": m.role,
                "status": m.status,
                "has_chosen": bool(m.choices_json),
                "confirmed_candidate_id": m.confirmed_candidate_id,
            }
            for m in members
        ],
    }


async def get_appointment_detail(db, appointment_id, user):
    return await detail(db, *(await access(db, appointment_id, user.id, False)))


async def list_appointments(db, user):
    mine = select(Member.appointment_id).where(Member.user_id == user.id)
    rows = await db.execute(
        select(Meal, Member, User.username)
        .join(Member, Member.appointment_id == Meal.id)
        .join(User, User.id == Member.user_id)
        .where(Meal.id.in_(mine))
        .order_by(Meal.created_at.desc(), Member.role)
    )
    grouped, names = {}, {}
    for meal, member, username in rows:
        grouped.setdefault(meal, []).append(member)
        names[member.user_id] = username
    return {
        "items": [
            await detail(db, m, ps, next(p for p in ps if p.user_id == user.id), names)
            for m, ps in grouped.items()
        ]
    }


async def notice_count(db, user):
    return {
        "unread": await db.scalar(
            select(func.count(Member.id)).where(
                Member.user_id == user.id, Member.notice.is_not(None)
            )
        )
    }


async def acknowledge(db, appointment_id, user):
    meal, members, viewer = await access(db, appointment_id, user.id)
    viewer.notice = None
    await db.commit()
    return await detail(db, meal, members, viewer)


def require(meal, *allowed):
    if state(meal) not in allowed:
        raise AppointmentError("INVALID_STATE", "约饭状态已变化，请刷新查看", 409)


async def create_appointment(db, user, body):
    organizer_schedule = await owned(db, body.schedule_id, user.id)
    try:
        organizer_calendar = timing_to_calendar(
            (organizer_schedule.parsed_json or {}).get("timing")
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise AppointmentError("TIMING_NOT_READY", str(exc), 409) from exc
    check_calendar(organizer_calendar, body.window)
    if body.window.date_to < now().astimezone(CAMPUS).date():
        raise AppointmentError("PAST_WINDOW", "不能邀请过去的日期", 400)
    if (body.window.date_to - now().astimezone(CAMPUS).date()).days > 366:
        raise AppointmentError("INVALID_WINDOW", "可约日期须在未来一年内", 400)
    invitee = await db.scalar(
        select(User).where(
            User.username == body.invitee_username,
            User.status == "active",
            User.is_active.is_(True),
            User.id != user.id,
        )
    )
    if not invitee:
        raise AppointmentError("INVITEE_NOT_FOUND", "找不到可邀请的圈友", 404)
    meal = Meal(
        organizer_id=user.id,
        title=body.title,
        location=body.location,
        status="pending",
        preferences=body.window.model_dump(mode="json"),
        candidates_json=[],
        expires_at=now() + 3 * DAY,
    )
    db.add(meal)
    await db.flush()
    members = [
        Member(
            appointment_id=meal.id,
            user_id=user.id,
            role="organizer",
            status="accepted",
            schedule_id=body.schedule_id,
            calendar=organizer_calendar,
        ),
        Member(
            appointment_id=meal.id,
            user_id=invitee.id,
            role="invitee",
            status="invited",
            notice="你收到了约饭邀请",
        ),
    ]
    db.add_all(members)
    await db.commit()
    return await detail(db, meal, members, members[0])


def fixed_times(schedule, body: FixedAppointmentCreateRequest):
    """把“第 N 周、周 X、第 A–B 节”换算成具体时区的起止时间。"""
    try:
        calendar = timing_to_calendar((schedule.parsed_json or {}).get("timing"))
    except (ValueError, KeyError, TypeError) as exc:
        raise AppointmentError("TIMING_NOT_READY", str(exc), 409) from exc
    anchor = date.fromisoformat(calendar["term_start"])
    periods = calendar["periods"]
    if body.lesson_end > len(periods):
        raise AppointmentError("UNKNOWN_PERIOD", "节次超出课表作息范围，请先核对作息", 409)
    day = anchor + timedelta(days=(body.week - 1) * 7 + body.weekday)
    start = datetime.combine(day, time.fromisoformat(periods[body.lesson_start - 1][0]), CAMPUS)
    end = datetime.combine(day, time.fromisoformat(periods[body.lesson_end - 1][1]), CAMPUS)
    if end <= start:
        raise AppointmentError("INVALID_TIME", "这个时段的作息时间不合法", 400)
    if start <= now().astimezone(CAMPUS):
        raise AppointmentError("PAST_WINDOW", "不能邀请过去的时间", 400)
    window = MealWindow(
        date_from=day,
        date_to=day,
        daily_start=periods[body.lesson_start - 1][0],
        daily_end=periods[body.lesson_end - 1][1],
        duration_minutes=int((end - start).total_seconds() // 60),
        buffer_minutes=0,
    )
    return window, start, end, calendar


async def create_fixed_appointment(db, user, body: FixedAppointmentCreateRequest):
    organizer_schedule = await owned(db, body.schedule_id, user.id)
    window, start, end, calendar = fixed_times(organizer_schedule, body)
    check_calendar(calendar, window)
    slots = (organizer_schedule.parsed_json or {}).get("slots", [])
    if any(
        not 1 <= s.get("lesson_start", 0) <= s.get("lesson_end", 0) <= len(calendar["periods"])
        for s in slots
    ):
        raise AppointmentError("UNKNOWN_PERIOD", "课表含作息范围外的节次，请先核对并编辑课表", 409)
    events = (
        await db.scalars(
            select(CalendarEvent).where(
                CalendarEvent.owner_id == user.id,
                CalendarEvent.ends_at >= start - DAY,
                CalendarEvent.starts_at < end + DAY,
            )
        )
    ).all()
    busy = busy_intervals(window, [(slots, calendar)], events)
    if not available(start, end, busy, 0 * MINUTE, now()):
        raise AppointmentError("TIME_BUSY", "你在这个时段已经有安排，请换一个空闲时段", 409)
    invitee = await db.scalar(
        select(User).where(
            User.username == body.invitee_username,
            User.status == "active",
            User.is_active.is_(True),
            User.id != user.id,
        )
    )
    if not invitee:
        raise AppointmentError("INVITEE_NOT_FOUND", "找不到可邀请的圈友", 404)
    existing_rows = await db.execute(
        select(Meal.id, Meal.preferences)
        .join(Member, Member.appointment_id == Meal.id)
        .where(
            Meal.organizer_id == user.id,
            Meal.status.in_(["pending", "confirmed"]),
            Member.user_id == invitee.id,
        )
    )
    for _, preferences in existing_rows.all():
        if (preferences or {}).get("mode") == "fixed" and preferences.get("fixed_start") == start.isoformat():
            raise AppointmentError("INVITATION_EXISTS", "这个时间已经邀请过 TA，请不要重复发送", 409)
    preferences = {
        **window.model_dump(mode="json"),
        "mode": "fixed",
        "fixed_start": start.isoformat(),
        "fixed_end": end.isoformat(),
        "fixed_week": body.week,
        "fixed_weekday": body.weekday,
        "fixed_lesson_start": body.lesson_start,
        "fixed_lesson_end": body.lesson_end,
    }
    meal = Meal(
        organizer_id=user.id,
        title=body.title,
        location=body.location,
        status="pending",
        preferences=preferences,
        candidates_json=[{"id": "fixed", "starts_at": start.isoformat(), "ends_at": end.isoformat()}],
        expires_at=now() + 3 * DAY,
    )
    db.add(meal)
    await db.flush()
    members = [
        Member(
            appointment_id=meal.id,
            user_id=user.id,
            role="organizer",
            status="accepted",
            schedule_id=body.schedule_id,
            calendar=calendar,
        ),
        Member(
            appointment_id=meal.id,
            user_id=invitee.id,
            role="invitee",
            status="invited",
            notice="你收到了一个时间约定邀请",
        ),
    ]
    db.add_all(members)
    await db.commit()
    return await detail(db, meal, members, members[0])


async def lock_owners(db, ids):
    # Same order for all bookings, even if two invitations select different schedules.
    await db.execute(select(User.id).where(User.id.in_(ids)).order_by(User.id).with_for_update())


async def occupancy(db, meal, members):
    window = MealWindow(**meal.preferences)
    ids = [p.user_id for p in members]
    await lock_owners(db, ids)
    calendars = []
    for p in members:
        schedule = await owned(db, p.schedule_id, p.user_id, lock=True)
        slots = (schedule.parsed_json or {}).get("slots", [])
        if (meal.preferences or {}).get("mode") == "group_fixed":
            if schedule.is_archived:
                raise AppointmentError("SCHEDULE_NOT_FOUND", "参与课表已存档，请重新选择课表", 409)
            try:
                p.calendar = timing_to_calendar((schedule.parsed_json or {}).get("timing"))
                check_calendar(p.calendar, window)
            except (ValueError, KeyError, TypeError) as exc:
                raise AppointmentError("TIMING_NOT_READY", "参与成员的课表作息已变化，请重新确认", 409) from exc
        if any(
            not 1
            <= s.get("lesson_start", 0)
            <= s.get("lesson_end", 0)
            <= len(p.calendar["periods"])
            for s in slots
        ):
            raise AppointmentError(
                "UNKNOWN_PERIOD", "参与课表含作息范围外的节次，请先核对并编辑课表", 409
            )
        calendars.append((slots, p.calendar))
    # Include adjacent days for travel buffers; each user can also have dated personal appointments.
    events = (
        await db.scalars(
            select(CalendarEvent).where(
                CalendarEvent.owner_id.in_(ids),
                CalendarEvent.ends_at >= window.date_from - DAY,
                CalendarEvent.starts_at < window.date_to + 2 * DAY,
            )
        )
    ).all()
    return window, busy_intervals(window, calendars, events)


async def respond(db, appointment_id, user, body):
    meal, members, viewer = await access(db, appointment_id, user.id)
    require(meal, "pending")
    if viewer.status != "invited":
        raise AppointmentError("INVALID_STATE", "没有等待你处理的邀请", 409)
    if body.accepted:
        invitee_schedule = await owned(db, body.schedule_id, user.id)
        try:
            invitee_calendar = timing_to_calendar(
                (invitee_schedule.parsed_json or {}).get("timing")
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise AppointmentError("TIMING_NOT_READY", str(exc), 409) from exc
        check_calendar(invitee_calendar, MealWindow(**meal.preferences))
        viewer.schedule_id = body.schedule_id
        viewer.calendar = invitee_calendar
        mode = (meal.preferences or {}).get("mode", "meal")
        if mode == "fixed":
            window, busy = await occupancy(db, meal, members)
            start = datetime.fromisoformat(meal.preferences["fixed_start"])
            end = datetime.fromisoformat(meal.preferences["fixed_end"])
            if not available(start, end, busy, 0 * MINUTE, now()):
                raise AppointmentError("APPOINTMENT_STALE", "这个时间已经有安排，请婉拒或让对方重新发起", 409)
            db.add_all(
                [
                    CalendarEvent(
                        owner_id=p.user_id,
                        appointment_id=meal.id,
                        title=meal.title,
                        location=meal.location,
                        starts_at=start,
                        ends_at=end,
                        buffer_minutes=0,
                    )
                    for p in members
                ]
            )
            meal.selected_candidate_id, meal.status = "fixed", "confirmed"
            viewer.status = "accepted"
            viewer.responded_at = now()
            for p in members:
                p.notice = "时间约定已确认，已加入我的日程"
            await db.commit()
            return await detail(db, meal, members, viewer)
        if mode == "group_fixed":
            viewer.status = "accepted"
            accepted_members = [p for p in members if p.status == "accepted"]
            _, busy = await occupancy(db, meal, accepted_members)
            start = datetime.fromisoformat(meal.preferences["fixed_start"])
            end = datetime.fromisoformat(meal.preferences["fixed_end"])
            if not available(start, end, busy, 0 * MINUTE, now()):
                raise AppointmentError("APPOINTMENT_STALE", "这个时间已经有安排，请婉拒或让对方重新发起", 409)
            viewer.responded_at = now()
            viewer.notice = None
            if len(accepted_members) == len(members):
                db.add_all([CalendarEvent(owner_id=p.user_id, appointment_id=meal.id,
                    title=meal.title, location=meal.location, starts_at=start, ends_at=end, buffer_minutes=0)
                    for p in members])
                meal.selected_candidate_id, meal.status = "fixed", "confirmed"
                for p in members:
                    p.notice = "群组约定已确认，已加入我的日程"
            else:
                for p in members:
                    if p.role == "organizer":
                        p.notice = "有成员接受了群组约定，等待其他成员回应"
            await db.commit()
            return await detail(db, meal, members, viewer)
        window, busy = await occupancy(db, meal, members)
        meal.candidates_json = recommend(window, busy, now())
        meal.status = "choosing"
    else:
        meal.status = "declined"
    viewer.status = "accepted" if body.accepted else "declined"
    viewer.notice = None
    for p in members:
        if p != viewer:
                p.notice = "对方已接受，请选择时间" if body.accepted else ("群组约定有成员婉拒，邀请已结束" if (meal.preferences or {}).get("mode") == "group_fixed" else "对方婉拒了这次邀请")
    viewer.responded_at = now()
    await db.commit()
    return await detail(db, meal, members, viewer)


async def choose(db, appointment_id, user, body):
    meal, members, viewer = await access(db, appointment_id, user.id)
    require(meal, "choosing", "confirming")
    choices = set(body.candidate_ids)
    if not choices <= {c["id"] for c in meal.candidates_json}:
        raise AppointmentError("INVALID_CANDIDATE", "候选已变化，请刷新并重新选择", 409)
    if choices != set(viewer.choices_json):
        viewer.choices_json = sorted(choices)
        for p in members:
            p.confirmed_candidate_id = None
            if p != viewer:
                p.notice = "对方已更新可接受时间"
    meal.status = "confirming" if common_ids(members) else "choosing"
    await db.commit()
    return await detail(db, meal, members, viewer)


async def confirm(db, appointment_id, user, body):
    meal, members, viewer = await access(db, appointment_id, user.id)
    if meal.status == "confirmed" and meal.selected_candidate_id == body.candidate_id:
        return await detail(db, meal, members, viewer)
    require(meal, "confirming")
    if body.candidate_id not in common_ids(members):
        raise AppointmentError("NOT_COMMON_CHOICE", "只能确认两个人都选过的时间", 409)
    viewer.confirmed_candidate_id = body.candidate_id
    if all(p.confirmed_candidate_id == body.candidate_id for p in members):
        window, busy = await occupancy(db, meal, members)
        c = next(c for c in meal.candidates_json if c["id"] == body.candidate_id)
        start, end = datetime.fromisoformat(c["starts_at"]), datetime.fromisoformat(c["ends_at"])
        instant = now()
        if not available(start, end, busy, window.buffer_minutes * MINUTE, instant):
            meal.status, meal.candidates_json = "choosing", recommend(window, busy, instant)
            for p in members:
                p.confirmed_candidate_id, p.choices_json = None, []
                p.notice = "有时间冲突，请重新选时"
            await db.commit()
            raise AppointmentError("APPOINTMENT_STALE", "时段已失效，已更新候选，请重新选择", 409)
        db.add_all(
            [
                CalendarEvent(
                    owner_id=p.user_id,
                    appointment_id=meal.id,
                    title=meal.title,
                    location=meal.location,
                    starts_at=start,
                    ends_at=end,
                    buffer_minutes=window.buffer_minutes,
                )
                for p in members
            ]
        )
        meal.selected_candidate_id, meal.status = body.candidate_id, "confirmed"
        for p in members:
            p.notice = "约饭已确认，已加入我的日程"
    else:
        for p in members:
            if p != viewer:
                p.notice = "对方已最终确认一个时段，请查看"
    await db.commit()
    return await detail(db, meal, members, viewer)


async def cancel(db, appointment_id, user):
    meal, members, viewer = await access(db, appointment_id, user.id)
    require(meal, "pending", "choosing", "confirming", "confirmed")
    await lock_owners(db, [p.user_id for p in members])
    await db.execute(delete(CalendarEvent).where(CalendarEvent.appointment_id == meal.id))
    for p in members:
        p.notice = None if p == viewer else "这次约饭已取消"
    meal.status = "cancelled"
    await db.commit()
    return await detail(db, meal, members, viewer)


def event_detail(e):
    return {
        "id": str(e.id),
        "title": e.title,
        "location": e.location,
        "appointment_id": str(e.appointment_id) if e.appointment_id else None,
        "starts_at": e.starts_at.astimezone(CAMPUS).isoformat(),
        "ends_at": e.ends_at.astimezone(CAMPUS).isoformat(),
    }


async def my_events(db, user):
    rows = await db.scalars(
        select(CalendarEvent)
        .where(CalendarEvent.owner_id == user.id)
        .order_by(CalendarEvent.starts_at)
    )
    return {"items": [event_detail(e) for e in rows]}


async def edit_event(db, user, event_id, body):
    await lock_owners(db, [user.id])
    if event_id:
        event = await db.scalar(
            select(CalendarEvent).where(
                CalendarEvent.id == event_id, CalendarEvent.owner_id == user.id
            )
        )
        if not event:
            raise AppointmentError("NOT_FOUND", "日程不存在", 404)
        if event.appointment_id:
            raise AppointmentError("LINKED_EVENT", "请在约饭详情中取消或重新约时间", 409)
    else:
        event = CalendarEvent(owner_id=user.id)
    if body is None:
        await db.delete(event)
    else:
        # Ensure a concurrent personal entry cannot silently double-book a confirmed meal.
        meals = (
            await db.scalars(
                select(CalendarEvent).where(
                    CalendarEvent.owner_id == user.id,
                    CalendarEvent.appointment_id.is_not(None),
                    CalendarEvent.starts_at < body.ends_at + DAY,
                    CalendarEvent.ends_at > body.starts_at - DAY,
                )
            )
        ).all()
        if any(
            body.starts_at < m.ends_at + m.buffer_minutes * MINUTE
            and body.ends_at > m.starts_at - m.buffer_minutes * MINUTE
            for m in meals
        ):
            raise AppointmentError("CALENDAR_CONFLICT", "这段时间已约饭（含路程时间）", 409)
        for k, v in body.model_dump().items():
            setattr(event, k, v)
        db.add(event)
    await db.commit()
    return event_detail(event) if body else {"deleted": True}
