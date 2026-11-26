"""Multi-member availability and fixed invitations with a rollback-only database."""

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_current_user
from app.api.v1.endpoints import schedule, schedule_groups
from app.core.config import settings
from app.core.database import get_db
from app.models.schedule import Schedule
from app.models.schedule_appointment import CalendarEvent
from app.models.schedule_group import ScheduleGroup, ScheduleGroupMember
from app.models.user import User
from app.services.schedule_timing import default_timing


@pytest.mark.skipif(os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires local PostgreSQL")
def test_group_availability_and_invitation_lifecycle(monkeypatch):
    async def feature_enabled(*_args):
        return None
    monkeypatch.setattr(schedule_groups, "require_schedule_feature", feature_enabled)

    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                outer = await connection.begin()
                try:
                    async with AsyncSession(bind=connection, expire_on_commit=False, autoflush=False, join_transaction_mode="create_savepoint") as db:
                        today = datetime.now(timezone(timedelta(hours=8))).date()
                        monday = today + timedelta(days=7 - today.weekday())
                        timing = default_timing()
                        timing["term_start"] = monday.isoformat()
                        timing["periods"][-1] = ["22:00", "22:10"]
                        ids = [uuid.uuid4() for _ in range(4)]
                        schedule_ids = [uuid.uuid4() for _ in range(3)]
                        group_id = uuid.uuid4()
                        users = [User(id=uid, username=f"g{uid.hex}", display_name=f"member-{i}", email=f"{uid}@example.test", hashed_password="unused", status="active", is_active=True, role="member") for i, uid in enumerate(ids)]
                        schedules = [Schedule(id=sid, owner_id=uid, original_name="shared", format="manual", parsed_json={"slots": [], "timing": timing}, is_public=False, is_archived=False) for sid, uid in zip(schedule_ids, ids)]
                        group = ScheduleGroup(id=group_id, name="test group", code=uuid.uuid4().hex[:8], owner_id=ids[0], join_mode="open")
                        members = [ScheduleGroupMember(group_id=group_id, user_id=uid, role="owner" if i == 0 else "member", status="active", schedule_id=schedule_ids[i]) for i, uid in enumerate(ids[:3])]
                        start = datetime.fromisoformat(monday.isoformat() + "T08:00:00+08:00")
                        busy_event = CalendarEvent(owner_id=ids[1], title="secret personal event", starts_at=start, ends_at=start + timedelta(minutes=45), buffer_minutes=0)
                        db.add_all(users)
                        await db.flush()
                        db.add_all([*schedules, group, *members, busy_event])
                        await db.commit()
                        app = FastAPI()
                        app.include_router(schedule_groups.router)
                        app.include_router(schedule.router)
                        current = {"user": SimpleNamespace(id=ids[0])}
                        app.dependency_overrides[get_current_user] = lambda: current["user"]
                        app.dependency_overrides[get_db] = lambda: db
                        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                            base = f"/schedule/groups/{group_id}"
                            body = {"week": 1, "member_ids": [str(ids[1]), str(ids[2])]}
                            current["user"] = SimpleNamespace(id=ids[3])
                            assert (await client.post(f"{base}/availability", json=body)).status_code == 404
                            current["user"] = SimpleNamespace(id=ids[0])
                            assert (await client.post(f"{base}/availability", json={**body, "member_ids": [str(ids[3])]})).status_code == 409
                            assert (await client.post(f"{base}/availability", json={**body, "member_ids": [str(ids[1]), str(ids[1])]})).status_code == 422
                            assert (await client.post(f"{base}/availability", json={**body, "member_ids": [str(ids[0])]})).status_code == 422
                            result = await client.post(f"{base}/availability", json=body)
                            assert result.status_code == 200, result.text
                            data = result.json()["data"]
                            assert data["member_count"] == 3
                            assert "secret personal event" not in result.text
                            assert not any(s["weekday"] == 0 and s["lesson"] == 1 for s in data["slots"])
                            assert any(s["weekday"] == 0 and s["lesson"] == 2 for s in data["slots"])
                            assert not any(s["lesson"] == 12 for s in data["slots"])
                            invite = {**body, "weekday": 0, "lesson_start": 2, "title": "meet"}
                            response = await client.post(f"{base}/appointments", json=invite)
                            assert response.status_code == 201, response.text
                            appointment_id = response.json()["data"]["id"]
                            assert response.json()["data"]["is_group"]
                            current["user"] = SimpleNamespace(id=ids[3])
                            assert (await client.get(f"/schedule/appointments/{appointment_id}")).status_code == 404
                            current["user"] = SimpleNamespace(id=ids[0])
                            assert (await client.post(f"{base}/appointments", json=invite)).status_code == 409
                            current["user"] = SimpleNamespace(id=ids[1])
                            response = await client.post(f"/schedule/appointments/{appointment_id}/response", json={"accepted": True, "schedule_id": str(schedule_ids[1])})
                            assert response.status_code == 200, response.text
                            assert response.json()["data"]["status"] == "pending"
                            assert not (await db.scalars(select(CalendarEvent).where(CalendarEvent.appointment_id == uuid.UUID(appointment_id)))).all()
                            late_start = datetime.fromisoformat(monday.isoformat() + "T" + timing["periods"][1][0] + ":00+08:00")
                            conflict_id = uuid.uuid4()
                            db.add(CalendarEvent(id=conflict_id, owner_id=ids[0], title="new conflict", starts_at=late_start, ends_at=late_start + timedelta(minutes=45), buffer_minutes=0))
                            await db.commit()
                            current["user"] = SimpleNamespace(id=ids[2])
                            conflict = await client.post(f"/schedule/appointments/{appointment_id}/response", json={"accepted": True, "schedule_id": str(schedule_ids[2])})
                            assert conflict.status_code == 409
                            await db.rollback()
                            assert not (await db.scalars(select(CalendarEvent).where(CalendarEvent.appointment_id == uuid.UUID(appointment_id)))).all()
                            conflict_event = await db.get(CalendarEvent, conflict_id)
                            await db.delete(conflict_event)
                            await db.commit()
                            response = await client.post(f"/schedule/appointments/{appointment_id}/response", json={"accepted": True, "schedule_id": str(schedule_ids[2])})
                            assert response.status_code == 200, response.text
                            assert response.json()["data"]["status"] == "confirmed"
                            events = (await db.scalars(select(CalendarEvent).where(CalendarEvent.appointment_id == uuid.UUID(appointment_id)))).all()
                            assert {e.owner_id for e in events} == set(ids[:3])
                            current["user"] = SimpleNamespace(id=ids[0])
                            assert (await client.post(f"/schedule/appointments/{appointment_id}/cancel")).status_code == 200
                            assert not (await db.scalars(select(CalendarEvent).where(CalendarEvent.appointment_id == uuid.UUID(appointment_id)))).all()
                            response = await client.post(f"{base}/appointments", json=invite)
                            assert response.status_code == 201
                            declined_id = response.json()["data"]["id"]
                            current["user"] = SimpleNamespace(id=ids[1])
                            response = await client.post(f"/schedule/appointments/{declined_id}/response", json={"accepted": False})
                            assert response.status_code == 200 and response.json()["data"]["status"] == "declined"
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()
    asyncio.run(exercise())
