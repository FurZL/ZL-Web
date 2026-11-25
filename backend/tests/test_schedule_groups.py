"""课表对比群组：纯统计与本地 PostgreSQL 流程测试。"""

from __future__ import annotations

import os
import uuid

import pytest

from app.services.schedule_group import _busy_stats


def _slot(name: str, weekday: int, start: int, end: int, weeks: list[int] | None = None, location: str = "") -> dict:
    return {
        "kind": "course",
        "name": name,
        "location": location,
        "campus": "下沙校区",
        "weekday": weekday,
        "lesson_start": start,
        "lesson_end": end,
        "weeks": weeks or [1],
    }


def test_busy_stats_counts_cells_and_same_classroom():
    mine = [_slot("我的课", 0, 1, 2, location="2-N101")]
    theirs = [_slot("他的课", 0, 2, 3, location="2-N101")]

    stats = _busy_stats(mine, theirs, week=1)

    assert stats["lesson_count"] == 12
    assert stats["both_busy"] == 1
    assert stats["both_free"] == 7 * 12 - 3
    assert stats["my_busy_only"] == 1
    assert stats["their_busy_only"] == 1
    assert stats["same_classroom"] == 1


@pytest.mark.skipif(
    os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires migrated local PostgreSQL"
)
def test_group_flow_with_local_postgres():
    from datetime import datetime
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.api.deps import get_current_user
    from app.api.v1.endpoints import schedule_groups
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
                        timing = {
                            "term_start": None,
                            "first_start": "08:00",
                            "lesson_minutes": 45,
                            "break_minutes": 10,
                            "periods": [
                                [f"{8 + i * 55 // 60:02}:{i * 55 % 60:02}", f"{8 + (45 + i * 55) // 60:02}:{(45 + i * 55) % 60:02}"]
                                for i in range(12)
                            ],
                        }
                        users, schedules = [], []
                        for index in range(4):
                            tag = uuid.uuid4().hex
                            u = User(
                                username=tag,
                                email=tag + "@example.test",
                                display_name=f"群成员 {index}",
                                hashed_password="test",
                                status="active",
                                is_active=True,
                            )
                            db.add(u)
                            await db.flush()
                            slots = [_slot(f"课程 {index}", 0, 1, 2, location="2-N101")]
                            if index == 1:
                                slots.append(
                                    {
                                        "kind": "event",
                                        "name": "秘密日程",
                                        "location": "",
                                        "campus": None,
                                        "weekday": 2,
                                        "lesson_start": 5,
                                        "lesson_end": 5,
                                        "weeks": [1],
                                    }
                                )
                            s = Schedule(
                                owner_id=u.id,
                                original_name=f"课表 {index}",
                                format="manual",
                                parsed_json={"slots": slots, "timing": timing, "revision": 0},
                                is_public=False,
                                is_archived=False,
                                sort_order=0,
                            )
                            db.add(s)
                            users.append(u)
                            schedules.append(s)
                        await db.flush()

                        app = FastAPI()
                        app.include_router(schedule_groups.router)
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
                                "POST", "schedule/groups", {"name": "周五课搭子", "join_mode": "open"}, 201
                            )
                            group_id = created["id"]
                            code = created["code"]
                            assert created["member_count"] == 1
                            assert created["my"]["role"] == "owner"

                            await call(
                                "PUT",
                                f"schedule/groups/{group_id}/schedule",
                                {"schedule_id": str(schedules[0].id)},
                            )

                            state["viewer"] = users[1]
                            joined = await call(
                                "POST", "schedule/groups/join", {"code": code.lower()}
                            )
                            assert joined["my"]["status"] == "active"
                            await call(
                                "PUT",
                                f"schedule/groups/{group_id}/schedule",
                                {"schedule_id": str(schedules[1].id)},
                            )

                            state["viewer"] = users[0]
                            detail = await call("GET", f"schedule/groups/{group_id}?week=1")
                            assert detail["member_count"] == 2
                            assert len(detail["members"]) == 2
                            other = next(m for m in detail["members"] if m["user_id"] == str(users[1].id))
                            assert other["stats"]["both_busy"] == 2
                            assert other["stats"]["same_classroom"] == 1
                            assert any(
                                slot["name"] == "已有安排"
                                for slot in other["slots"]
                                if slot["kind"] == "event"
                            )
                            assert not any(
                                slot["name"] == "秘密日程" for slot in other["slots"]
                            )

                            await call(
                                "PATCH", f"schedule/groups/{group_id}", {"join_mode": "approval"}
                            )
                            state["viewer"] = users[2]
                            pending = await call(
                                "POST", "schedule/groups/join", {"code": code}
                            )
                            assert pending["my"]["status"] == "pending"
                            pending_detail = await call(
                                "GET", f"schedule/groups/{group_id}"
                            )
                            assert pending_detail["members"] == []
                            assert pending_detail["code"] is None
                            assert pending_detail["my"]["status"] == "pending"

                            state["viewer"] = users[0]
                            before = await call("GET", f"schedule/groups/{group_id}")
                            assert before["pending_count"] == 1
                            await call(
                                "POST",
                                f"schedule/groups/{group_id}/members/{users[2].id}/approve",
                            )
                            approved = await call("GET", f"schedule/groups/{group_id}")
                            assert len(approved["members"]) == 3

                            state["viewer"] = users[2]
                            await call(
                                "PUT",
                                f"schedule/groups/{group_id}/schedule",
                                {"schedule_id": str(schedules[2].id)},
                            )

                            state["viewer"] = users[0]
                            await call(
                                "DELETE", f"schedule/groups/{group_id}/members/{users[2].id}"
                            )
                            removed = await call("GET", f"schedule/groups/{group_id}")
                            assert len(removed["members"]) == 2

                            state["viewer"] = users[2]
                            await call("GET", f"schedule/groups/{group_id}", status=404)

                            state["viewer"] = users[0]
                            await call(
                                "DELETE",
                                f"schedule/groups/{group_id}/members/{users[0].id}",
                                status=409,
                            )
                            await call("DELETE", f"schedule/groups/{group_id}")
                            await call("GET", f"schedule/groups/{group_id}", status=404)
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()

    import asyncio

    asyncio.run(exercise())
