"""Run the API transaction test with MEAL_TEST_LOCAL_DB=1 after alembic upgrade head."""

import asyncio
import os
import uuid
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.schemas.schedule import MealWindow
from app.services.meal_times import CAMPUS, MINUTE, available, busy_intervals, clock, recommend


def test_week_and_private_blocks_and_exact_boundaries():
    day = date(2027, 3, 8)
    w = MealWindow(
        date_from=day,
        date_to=day,
        daily_start="11:00",
        daily_end="14:00",
        duration_minutes=60,
        buffer_minutes=10,
    )
    calendar = {"term_start": "2027-03-01", "periods": [("11:00", "11:36")] * 12}
    slot = {"weekday": 0, "weeks": [2], "kind": "event", "lesson_start": 1, "lesson_end": 1}
    e = SimpleNamespace(
        starts_at=clock(day, "13:21"), ends_at=clock(day, "14:00"), buffer_minutes=15
    )
    busy = busy_intervals(w, [([slot, dict(slot, weeks=[1])], calendar)], [e])
    instant = clock(day, "10:00")
    options = recommend(w, busy, instant)
    assert options and all(
        available(
            datetime.fromisoformat(c["starts_at"]),
            datetime.fromisoformat(c["ends_at"]),
            busy,
            10 * MINUTE,
            instant,
        )
        for c in options
    )
    assert any("11:46" in c["starts_at"] for c in options)
    assert not recommend(w, busy, clock(day, "14:00"))
    assert not busy_intervals(w, [([dict(slot, weeks=[1])], calendar)], [])


@pytest.mark.skipif(
    os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires migrated local PostgreSQL"
)
def test_meal_api_with_private_schedules():
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.api.deps import get_current_user
    from app.api.v1.endpoints.schedule import router
    from app.core.config import settings
    from app.core.database import get_db
    from app.models.schedule import Schedule
    from app.models.user import User

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
                        day = datetime.now(CAMPUS).date() + timedelta(days=4)
                        anchor = day - timedelta(days=day.weekday())

                        def hh(m):
                            return f"{m // 60:02}:{m % 60:02}"

                        users, schedules = [], []
                        for _ in range(3):
                            tag = uuid.uuid4().hex
                            u = User(
                                username=tag,
                                email=tag + "@example.test",
                                display_name="Meal test",
                                hashed_password="test",
                                status="active",
                                is_active=True,
                            )
                            db.add(u)
                            await db.flush()
                            timing = {
                                "term_start": anchor.isoformat(),
                                "first_start": "08:00",
                                "lesson_minutes": 45,
                                "break_minutes": 10,
                                "periods": [
                                    [hh(480 + i * 55), hh(525 + i * 55)] for i in range(12)
                                ],
                            }
                            s = Schedule(
                                owner_id=u.id,
                                original_name="private",
                                format="manual",
                                is_public=False,
                                parsed_json={"slots": [], "timing": timing, "revision": 0},
                            )
                            db.add(s)
                            users.append(u)
                            schedules.append(s)
                        await db.flush()
                        app = FastAPI()
                        app.include_router(router)
                        app.dependency_overrides[get_db] = lambda: db
                        viewer = users[0]
                        app.dependency_overrides[get_current_user] = lambda: viewer
                        async with AsyncClient(
                            transport=ASGITransport(app=app), base_url="http://test/schedule/"
                        ) as api:

                            async def call(method, path, data=None, status=200):
                                res = await api.request(method, path, json=data)
                                assert res.status_code == status, res.text
                                return res.json().get("data")

                            window = {
                                "date_from": str(day),
                                "date_to": str(day + timedelta(days=2)),
                                "daily_start": "11:00",
                                "daily_end": "14:00",
                                "duration_minutes": 60,
                            }
                            create = {
                                "invitee_username": users[1].username,
                                "schedule_id": str(schedules[0].id),
                                "window": window,
                            }
                            m = await call("POST", "appointments", create, 201)
                            path = "appointments/" + m["id"]
                            assert m["status"] == "pending" and not m["candidates"]
                            viewer = users[2]
                            await call("GET", path, status=404)
                            assert not (await call("GET", "appointments"))["items"]
                            viewer = users[1]
                            await call(
                                "POST",
                                path + "/response",
                                {
                                    "accepted": True,
                                    "schedule_id": str(schedules[0].id),
                                },
                                409,
                            )
                            m = await call(
                                "POST",
                                path + "/response",
                                {
                                    "accepted": True,
                                    "schedule_id": str(schedules[1].id),
                                },
                            )
                            assert 3 <= len(m["candidates"]) <= 5 and "private" not in str(m)

                            async def select_and_confirm_first(c):
                                nonlocal viewer
                                for viewer in users[:2]:
                                    await call(
                                        "POST", path + "/choices", {"candidate_ids": [c["id"]]}
                                    )
                                viewer = users[0]
                                first = await call(
                                    "POST", path + "/confirm", {"candidate_id": c["id"]}
                                )
                                assert (
                                    first["status"] == "confirming"
                                    and not (await call("GET", "calendar"))["items"]
                                )
                                viewer = users[1]

                            c = m["candidates"][0]
                            await select_and_confirm_first(c)
                            private_event = {
                                "title": "private appointment",
                                "starts_at": c["starts_at"],
                                "ends_at": c["ends_at"],
                            }
                            personal = await call("POST", "calendar", private_event, 201)
                            await call("POST", path + "/confirm", {"candidate_id": c["id"]}, 409)
                            refreshed = await call("GET", path)
                            assert (
                                refreshed["status"] == "choosing"
                                and not refreshed["common_candidate_ids"]
                                and c not in refreshed["candidates"]
                            )
                            c = refreshed["candidates"][0]
                            await select_and_confirm_first(c)
                            for _ in range(2):
                                assert (
                                    await call("POST", path + "/confirm", {"candidate_id": c["id"]})
                                )["status"] == "confirmed"
                            for viewer in users[:2]:
                                entries = (await call("GET", "calendar"))["items"]
                                assert (
                                    len([e for e in entries if e["appointment_id"] == m["id"]]) == 1
                                )
                                if viewer is users[0]:
                                    assert all(e["title"] != "private appointment" for e in entries)
                                assert (await call("GET", "meal-notices"))["unread"] == 1
                                assert not (await call("POST", path + "/read"))["notice"]
                                assert (await call("GET", "meal-notices"))["unread"] == 0
                            await call(
                                "DELETE",
                                "calendar/" + next(e["id"] for e in entries if e["appointment_id"]),
                                status=409,
                            )
                            viewer = users[0]
                            await call("DELETE", "calendar/" + personal["id"], status=404)
                            # A separate invitation must exclude the already confirmed meal.
                            m2 = await call("POST", "appointments", create, 201)
                            viewer = users[1]
                            m2 = await call(
                                "POST",
                                "appointments/" + m2["id"] + "/response",
                                {
                                    "accepted": True,
                                    "schedule_id": str(schedules[1].id),
                                },
                            )
                            assert all(
                                item["ends_at"] <= c["starts_at"]
                                or item["starts_at"] >= c["ends_at"]
                                for item in m2["candidates"]
                            )
                            assert (await call("POST", path + "/cancel"))["status"] == "cancelled"
                            assert [e["id"] for e in (await call("GET", "calendar"))["items"]] == [
                                personal["id"]
                            ]
                            await call("DELETE", "calendar/" + personal["id"])
                            viewer = users[0]
                            assert not (await call("GET", "calendar"))["items"]
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()

    asyncio.run(exercise())
