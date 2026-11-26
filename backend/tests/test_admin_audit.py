"""Administrative audit integration tests use a rolled-back local transaction."""

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_current_user
from app.api.v1.endpoints import admin_audit, admin_events, admin_images, admin_settings, admin_users, announcements, club, pages
from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.content import Announcement, DynamicPage
from app.models.event import Event
from app.models.image import Image
from app.models.user import User


@pytest.mark.skipif(os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires local PostgreSQL")
def test_admin_audit_coverage_privacy_authorization_and_pagination():
    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                outer = await connection.begin()
                try:
                    async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                        uid = uuid.uuid4()
                        user = User(id=uid, username=f"audit-{uid}", display_name="test", email=f"{uid}@example.test", hashed_password="secret-hash", status="active", is_active=True, role="member")
                        image = Image(id=uuid.uuid4(), stored_object_id=uuid.uuid4(), uploader_id=uid, moderation_status="pending", is_public=False)
                        announcement = Announcement(id=uuid.uuid4(), title="private title", content="secret body", status="draft", is_pinned=False)
                        now = datetime.now(timezone.utc)
                        activity = Event(id=uuid.uuid4(), title="private event", starts_at=now, ends_at=now + timedelta(hours=1), status="draft")
                        page = DynamicPage(id=uuid.uuid4(), slug=f"audit-{uid}", title="secret page", status="draft", schema_json={})
                        db.add_all([user, image, announcement, activity, page])
                        await db.commit()
                        actor = SimpleNamespace(id=uuid.uuid4(), role="admin")
                        app = FastAPI()
                        for router in (admin_audit.router, admin_users.router, admin_settings.router, admin_images.router, admin_events.router, announcements.router, pages.router, club.router):
                            app.include_router(router)
                        app.dependency_overrides[get_db] = lambda: db
                        app.dependency_overrides[get_current_user] = lambda: actor
                        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                            actor.role = "member"
                            assert (await client.get("/admin/audit")).status_code == 403
                            assert (await client.patch(f"/admin/users/{uid}/role", json={"role": "photographer"})).status_code == 403
                            actor.role = "admin"
                            for path in ("/admin/users/", "/admin/users/pending", "/admin/settings/", "/admin/images/", "/admin/images/stats", "/admin/events/"):
                                response = await client.get(path)
                                assert response.status_code == 200, (path, response.text)
                            assert (await client.patch(f"/admin/users/{uid}/role", json={"role": "photographer"})).status_code == 200
                            assert (await client.patch(f"/admin/users/{uid}/status", json={"status": "disabled"})).status_code == 200
                            key = f"audit-{uid}"
                            assert (await client.put("/admin/settings/", json={"key": key, "value": {"password": "secret-setting"}})).status_code == 200
                            assert (await client.patch(f"/admin/images/{image.id}/moderation", json={"moderation_status": "approved"})).status_code == 200
                            assert (await client.patch(f"/announcements/admin/{announcement.id}", json={"content": "new-secret-body", "is_pinned": True})).status_code == 200
                            assert (await client.patch(f"/admin/events/{activity.id}/status", json={"status": "published"})).status_code == 200
                            assert (await client.post(f"/pages/admin/{page.id}/publish")).status_code == 200
                            created = await client.post("/announcements/admin", json={"title": "new title", "content": "new secret"})
                            assert created.status_code == 200
                            created_id = created.json()["data"]["id"]
                            created_page = await client.post("/pages/admin", json={"slug": f"audit-new-{uid}", "title": "new page", "page_schema": {}})
                            assert created_page.status_code == 200
                            response = await client.get("/admin/audit", params={"actor_id": str(actor.id), "page_size": 2})
                            assert response.status_code == 200, response.text
                            payload = response.json()["data"]
                            assert payload["total"] == 9
                            assert len(payload["items"]) == 2
                            assert (await client.get("/admin/audit", params={"actor_id": str(actor.id), "page": 4, "page_size": 2})).json()["data"]["items"]
                            filtered = (await client.get("/admin/audit", params={"actor_id": str(actor.id), "target_type": "user", "action": "user.set_role"})).json()["data"]
                            assert filtered["total"] == 1
                            assert filtered["items"][0]["changes"]["before"]["role"] == "member"
                            assert filtered["items"][0]["changes"]["after"]["role"] == "photographer"
                            assert (await client.get("/admin/audit", params={"start": "2026-01-01T00:00:00"})).status_code == 422
                            logs = (await db.scalars(select(AuditLog).where(AuditLog.actor_user_id == actor.id))).all()
                            assert len(logs) == 9
                            assert any(row.target_id == created_id and row.action == "announcement.create_announcement" for row in logs)
                            assert any(row.target_id == created_page.json()["data"]["id"] and row.action == "page.create_page" for row in logs)
                            serialized = str([row.metadata_json for row in logs])
                            for secret in ("secret-hash", "secret-setting", "secret body", "new-secret-body", user.email):
                                assert secret not in serialized
                            def fail_audit(_mapper, _connection, _target):
                                raise RuntimeError("audit unavailable")
                            event.listen(AuditLog, "before_insert", fail_audit)
                            try:
                                with pytest.raises(RuntimeError, match="audit unavailable"):
                                    await client.patch(f"/admin/users/{uid}/role", json={"role": "member"})
                            finally:
                                event.remove(AuditLog, "before_insert", fail_audit)
                            await db.rollback()
                            await db.refresh(user)
                            assert user.role == "photographer"
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()
    asyncio.run(exercise())
