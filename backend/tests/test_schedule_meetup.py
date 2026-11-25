"""从课表空闲时段直接发起固定时间邀请的流程测试。"""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, time, timedelta

import pytest

from app.services.meal_times import CAMPUS


@pytest.mark.skipif(
    os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires migrated local PostgreSQL"
)
def test_fixed_appointment_flow_with_local_postgres():
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.api.deps import get_current_user
    from app.api.v1.endpoints import schedule
    from app.core.config import settings
    from app.core.database import get_db
    from app.models.schedule import Schedule
    from app.models.user import User
    from app.services.schedule_timing import default_timing

    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as conn:
                outer = await conn.begin()
                try:
                    async with AsyncSession(
                        bind=conn,
                        expire_on_commit=False,
                        autoflush=False,
                        join_transaction_mode="create_savepoint",
                    ) as db:
                        anchor = date.today() - timedelta(days=date.today().weekday())
                        timing = {**default_timing(), "term_start": anchor.isoformat()}
                        users, schedules = [], []
                        for index in range(2):
                            tag = uuid.uuid4().hex
                            u = User(
                                username=tag,
                                email=tag + "@example.test",
                                display_name=f"约定测试 {index}",
                                hashed_password="test",
                                status="active",
                                is_active=True,
                            )
                            db.add(u)
                            await db.flush()
                            s = Schedule(
                                owner_id=u.id,
                                original_name="约定课表",
                                format="manual",
                                parsed_json={"slots": [], "timing": timing, "revision": 0},
                                is_public=False,
                                is_archived=False,
                                sort_order=0,
                            )
                            db.add(s)
                            users.append(u)
                            schedules.append(s)
                        await db.flush()

                        app = FastAPI()
                        app.include_router(schedule.router)
                        state = {"viewer": users[0]}
                        app.dependency_overrides[get_db] = lambda: db
                        app.dependency_overrides[get_current_user] = lambda: state["viewer"]
                        async with AsyncClient(
                            transport=ASGITransport(app=app), base_url="http://test/"
                        ) as api:

                            async def call(method, path, data=None, status=200):
                                response = await api.request(method, path, json=data)
                                assert response.status_code == status, response.text
                                return response.json().get("data")

                            created = await call(
                                "POST",
                                "schedule/appointments/fixed",
                                {
                                    "schedule_id": str(schedules[0].id),
                                    "invitee_username": users[1].username,
                                    "title": "一起自习",
                                    "week": 2,
                                    "weekday": 2,
                                    "lesson_start": 1,
                                    "lesson_end": 2,
                                },
                                201,
                            )
                            assert created["mode"] == "fixed"
                            assert created["status"] == "pending"
                            expected_day = anchor + timedelta(days=9)
                            start = datetime.combine(expected_day, time(8, 0), CAMPUS)
                            end = datetime.combine(expected_day, time(9, 40), CAMPUS)
                            assert created["fixed"]["starts_at"] == start.isoformat()
                            assert created["fixed"]["ends_at"] == end.isoformat()
                            assert created["fixed"]["week"] == 2
                            assert created["fixed"]["weekday"] == 2
                            assert created["fixed"]["lesson_start"] == 1
                            assert created["fixed"]["lesson_end"] == 2

                            await call(
                                "POST",
                                "schedule/appointments/fixed",
                                {
                                    "schedule_id": str(schedules[0].id),
                                    "invitee_username": users[1].username,
                                    "title": "一起自习",
                                    "week": 2,
                                    "weekday": 2,
                                    "lesson_start": 1,
                                    "lesson_end": 2,
                                },
                                409,
                            )

                            state["viewer"] = users[1]
                            accepted = await call(
                                "POST",
                                f"schedule/appointments/{created['id']}/response",
                                {"accepted": True, "schedule_id": str(schedules[1].id)},
                            )
                            assert accepted["status"] == "confirmed"
                            assert accepted["selected_candidate_id"] == "fixed"

                            for viewer, schedule_model in zip(users, schedules):
                                state["viewer"] = viewer
                                calendar = await call("GET", "schedule/calendar")
                                events = calendar["items"] if isinstance(calendar, dict) else calendar
                                matches = [
                                    e
                                    for e in events
                                    if e.get("appointment_id") == created["id"]
                                ]
                                assert len(matches) == 1
                                assert matches[0]["title"] == "一起自习"
                                assert matches[0]["starts_at"] == start.isoformat()

                            state["viewer"] = users[0]
                            cancelled = await call(
                                "POST", f"schedule/appointments/{created['id']}/cancel"
                            )
                            assert cancelled["status"] == "cancelled"
                            calendar = await call("GET", "schedule/calendar")
                            events = calendar["items"] if isinstance(calendar, dict) else calendar
                            assert not [e for e in events if e.get("appointment_id") == created["id"]]
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()

    import asyncio

    asyncio.run(exercise())
