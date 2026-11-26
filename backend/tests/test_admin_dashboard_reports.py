"""Administrative dashboard, permissions, report handling and audit integration."""

import asyncio
import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_current_user
from app.api.v1.endpoints import admin_dashboard, admin_images, admin_users, images
from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.event import EventRegistration
from app.models.image import Image
from app.models.report import Report
from app.models.user import User


@pytest.mark.skipif(os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires local PostgreSQL")
def test_dashboard_reports_and_user_permissions():
    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                outer = await connection.begin()
                try:
                    async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                        actor = SimpleNamespace(id=uuid.uuid4(), role="admin")
                        uid = uuid.uuid4()
                        pending_id = uuid.uuid4()
                        user = User(id=uid, username=f"test-{uid}", display_name="member", email=f"{uid}@example.test", hashed_password="unused", status="active", is_active=True, role="member")
                        pending = User(id=pending_id, username=f"test-{pending_id}", display_name="pending", email=f"{pending_id}@example.test", hashed_password="unused", status="pending", is_active=False, role="member")
                        protected_id = uuid.uuid4()
                        protected = User(id=protected_id, username=f"test-{protected_id}", display_name="moderator", email=f"{protected_id}@example.test", hashed_password="unused", status="disabled", is_active=False, role="moderator")
                        img = Image(id=uuid.uuid4(), stored_object_id=uuid.uuid4(), uploader_id=uid, moderation_status="approved", is_public=True, original_name="test.jpg")
                        first = Report(id=uuid.uuid4(), target_type="image", target_id=str(img.id), reporter_id=actor.id, status="open", reason="inappropriate")
                        second = Report(id=uuid.uuid4(), target_type="image", target_id=str(uuid.uuid4()), reporter_id=actor.id, status="open", reason="inappropriate")
                        regs = [EventRegistration(id=uuid.uuid4(), event_id=uuid.uuid4(), user_id=uid, status=s, idempotency_key=str(uuid.uuid4())) for s in ("registered", "checked_in", "waitlisted", "cancelled")]
                        db.add_all([user, pending, protected, img, first, second, *regs])
                        await db.commit()
                        app = FastAPI()
                        for router in (admin_dashboard.router, admin_images.router, admin_users.router, images.router):
                            app.include_router(router)
                        app.dependency_overrides[get_db] = lambda: db
                        app.dependency_overrides[get_current_user] = lambda: actor
                        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                            actor.role = "member"
                            assert (await client.get("/admin/dashboard/overview")).status_code == 403
                            assert (await client.get("/admin/images/reports")).status_code == 403
                            assert (await client.patch(f"/admin/images/reports/{first.id}", json={"outcome": "hide"})).status_code == 403
                            actor.role = "admin"
                            stats = (await client.get("/admin/dashboard/overview")).json()["data"]
                            expected = await db.scalar(select(func.count()).select_from(EventRegistration).where(EventRegistration.status.in_(["registered", "checked_in"])))
                            assert stats["registrations"] == expected
                            assert stats["open_reports"] >= 2
                            response = await client.get("/admin/images/reports", params={"status": "open", "page_size": 50})
                            assert response.status_code == 200
                            items = response.json()["data"]["items"]
                            assert any(item["id"] == str(first.id) and item["image_exists"] for item in items)
                            assert (await client.patch(f"/admin/users/{pending_id}/status", json={"status": "active"})).status_code == 409
                            assert (await client.patch(f"/admin/users/{pending_id}/role", json={"role": "photographer"})).status_code == 409
                            assert (await client.post(f"/admin/users/{uid}/reject")).status_code == 409
                            assert (await client.patch(f"/admin/users/{uid}/role", json={"role": "admin"})).status_code == 403
                            assert (await client.patch(f"/admin/users/{protected_id}/status", json={"status": "active"})).status_code == 403
                            assert (await client.patch(f"/admin/users/{uid}/role", json={"role": "photographer"})).status_code == 200
                            assert (await client.patch(f"/admin/users/{uid}/status", json={"status": "disabled"})).status_code == 200
                            assert (await client.patch(f"/admin/users/{uid}/status", json={"status": "active"})).status_code == 200
                            assert (await client.patch(f"/admin/images/reports/{second.id}", json={"outcome": "hide"})).status_code == 404
                            assert (await client.patch(f"/admin/images/reports/{second.id}", json={"outcome": "dismissed"})).status_code == 200
                            assert (await client.patch(f"/admin/images/reports/{first.id}", json={"outcome": "hide"})).status_code == 200
                            await db.refresh(img)
                            assert img.moderation_status == "rejected" and not img.is_public
                            assert (await client.patch(f"/admin/images/reports/{first.id}", json={"outcome": "handled"})).status_code == 409
                            assert (await client.post(f"/images/{img.id}/report")).status_code == 404
                            records = (await db.scalars(select(AuditLog).where(AuditLog.actor_user_id == actor.id))).all()
                            assert any(row.target_id == str(first.id) and row.target_type == "report" and row.metadata_json["after"]["status"] == "handled" for row in records)
                            assert any(row.target_id == str(img.id) and row.target_type == "image" and row.metadata_json["after"]["is_public"] is False for row in records)
                            after = (await client.get("/admin/dashboard/overview")).json()["data"]
                            assert after["open_reports"] == stats["open_reports"] - 2
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()
    asyncio.run(exercise())
