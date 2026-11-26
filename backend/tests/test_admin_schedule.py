"""Schedule administration integration, rolled back after each run."""

import asyncio
import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_current_user
from app.api.v1.endpoints import admin_schedule, admin_settings, schedule, schedule_groups, site
from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.services.schedule_config import ScheduleConfig


@pytest.mark.skipif(os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires local PostgreSQL")
def test_schedule_settings_authorization_enforcement_and_audit():
    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                outer = await connection.begin()
                try:
                    async with AsyncSession(
                        bind=connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    ) as db:
                        viewer = SimpleNamespace(id=uuid.uuid4(), role="member")
                        app = FastAPI()
                        for router in (
                            admin_schedule.router,
                            admin_settings.router,
                            schedule_groups.router,
                            schedule.router,
                            site.router,
                        ):
                            app.include_router(router)
                        app.dependency_overrides[get_db] = lambda: db
                        app.dependency_overrides[get_current_user] = lambda: viewer
                        async with AsyncClient(
                            transport=ASGITransport(app=app), base_url="http://test"
                        ) as client:
                            assert (await client.get("/admin/schedule/overview")).status_code == 403
                            assert (await client.get("/admin/schedule/audit")).status_code == 403
                            viewer.role = "admin"
                            assert (
                                await client.put("/admin/schedule/config", json={})
                            ).status_code == 422
                            assert (
                                await client.put(
                                    "/admin/settings/", json={"key": "schedule_config", "value": {}}
                                )
                            ).status_code == 400
                            disabled = {key: False for key in ScheduleConfig.model_fields}
                            response = await client.put("/admin/schedule/config", json=disabled)
                            assert response.status_code == 200, response.text
                            assert response.json()["data"] == disabled
                            public = await client.get("/site/public-config")
                            assert public.json()["data"]["schedule_config"] == disabled
                            assert (await client.get("/admin/schedule/overview")).status_code == 200
                            audit = await client.get("/admin/schedule/audit")
                            assert audit.status_code == 200
                            assert audit.json()["data"]["items"][0]["changes"]["after"] == disabled
                            viewer.role = "member"
                            requests = [
                                (
                                    "POST",
                                    "/schedule/upload-intent",
                                    {"filename": "a.txt", "size_bytes": 1},
                                ),
                                (
                                    "POST",
                                    "/schedule/upload-complete",
                                    {"bucket": "x", "object_key": "x", "original_name": "x.txt"},
                                ),
                                ("POST", "/schedule/groups", {"name": "测试"}),
                                ("POST", "/schedule/groups/join", {"code": "ABCDEFGH"}),
                                (
                                    "PATCH",
                                    f"/schedule/{uuid.uuid4()}/visibility",
                                    {"is_public": True},
                                ),
                                (
                                    "POST",
                                    "/schedule/appointments/fixed",
                                    {
                                        "schedule_id": str(uuid.uuid4()),
                                        "invitee_username": "test",
                                        "week": 1,
                                        "weekday": 1,
                                        "lesson_start": 1,
                                        "lesson_end": 2,
                                    },
                                ),
                            ]
                            for method, path, payload in requests:
                                response = await client.request(method, path, json=payload)
                                assert response.status_code == 403, (path, response.text)
                                assert (
                                    response.json()["detail"]["code"] == "SCHEDULE_FEATURE_DISABLED"
                                )
                            response = await client.post(
                                "/schedule/pdf-preview",
                                files={"file": ("test.pdf", b"pdf", "application/pdf")},
                            )
                            assert response.status_code == 403
                            # Disabling new sharing must not prevent withdrawing an existing share.
                            response = await client.patch(
                                f"/schedule/{uuid.uuid4()}/visibility", json={"is_public": False}
                            )
                            assert response.status_code == 404
                            assert (await client.get("/schedule/groups")).status_code == 200
                            rows = (
                                await db.scalars(
                                    select(AuditLog).where(
                                        AuditLog.action == "schedule.config.update",
                                        AuditLog.actor_user_id == viewer.id,
                                    )
                                )
                            ).all()
                            assert len(rows) == 1
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()

    asyncio.run(exercise())
