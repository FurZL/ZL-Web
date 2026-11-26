"""Durable image tasks, leases, retries and transactional enqueue."""

import asyncio
import io
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image as PillowImage
from sqlalchemy import event, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.api.deps import get_current_user
from app.api.v1.endpoints import admin_images
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.image import ProfileImage, StoredObject
from app.models.image_job import ImageProcessingJob
from app.providers.storage.base import ObjectHead
from app.services import image_processing, profile_image
from app.workers import image_worker


@pytest.mark.skipif(os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires local PostgreSQL")
def test_job_enqueue_lease_recovery_and_retry(monkeypatch):
    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                outer = await connection.begin()
                try:
                    def session():
                        return AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
                    monkeypatch.setattr(image_worker, "async_session_factory", session)

                    class Storage:
                        bucket = "test-bucket"
                        async def head_object(self, *_):
                            return ObjectHead(exists=True, size_bytes=10, content_type="image/png")

                    monkeypatch.setattr(profile_image, "get_storage_provider", lambda: Storage())
                    async with session() as db:
                        user = SimpleNamespace(id=uuid.uuid4())
                        image = await profile_image.complete_profile_upload(db, user=user, object_key=f"private/profiles/{user.id}/test", bucket="test-bucket", original_name="test.png")
                        image_id = image.id
                        job = await db.scalar(select(ImageProcessingJob).where(ImageProcessingJob.image_id == image_id))
                        assert job and job.status == "pending" and job.attempts == 0
                        job_id = job.id
                    claimed = await image_worker._claim()
                    assert claimed and claimed[0] == job_id and claimed[4] == 1
                    assert await image_worker._claim() is None
                    async with session() as db:
                        job = await db.get(ImageProcessingJob, job_id)
                        job.lease_until = datetime.now(timezone.utc) - timedelta(seconds=1)
                        await db.commit()
                    reclaimed = await image_worker._claim()
                    assert reclaimed and reclaimed[4] == 2 and reclaimed[3] != claimed[3]
                    await image_worker._finish(job_id, claimed[3], 1, True)
                    async with session() as db:
                        job = await db.get(ImageProcessingJob, job_id)
                        assert job.status == "processing" and job.lease_token == reclaimed[3]
                    await image_worker._finish(job_id, reclaimed[3], 2, False)
                    async with session() as db:
                        job = await db.get(ImageProcessingJob, job_id)
                        assert job.status == "pending" and job.next_attempt_at > datetime.now(timezone.utc)
                        job.attempts = image_worker.MAX_ATTEMPTS
                        job.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                        await db.commit()
                    assert await image_worker._claim() is None
                    async with session() as db:
                        job = await db.get(ImageProcessingJob, job_id)
                        image = await db.get(ProfileImage, image_id)
                        stored = await db.get(StoredObject, image.stored_object_id)
                        assert job.status == "failed" and stored.processing_status == "failed"

                        actor = SimpleNamespace(id=uuid.uuid4(), role="moderator")
                        app = FastAPI()
                        app.include_router(admin_images.router)
                        app.dependency_overrides[get_db] = lambda: db
                        app.dependency_overrides[get_current_user] = lambda: actor
                        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                            assert (await client.get("/admin/images/processing-jobs")).status_code == 403
                            actor.role = "admin"
                            assert (await client.get("/admin/images/processing-jobs", params={"status": "failed"})).status_code == 200
                            assert (await client.post(f"/admin/images/processing-jobs/{job_id}/retry")).status_code == 200
                            assert (await client.post(f"/admin/images/processing-jobs/{job_id}/retry")).status_code == 409
                            await db.refresh(job)
                            await db.refresh(stored)
                            assert job.status == "pending" and job.attempts == 0 and stored.processing_status == "pending"
                            audit = await db.scalar(select(AuditLog).where(AuditLog.actor_user_id == actor.id, AuditLog.target_id == str(job_id)))
                            assert audit and audit.action == "image_job.retry_processing_job"

                    def fail_job(_mapper, _connection, _target):
                        raise RuntimeError("job insert failed")
                    event.listen(ImageProcessingJob, "before_insert", fail_job)
                    failed_key = f"private/profiles/{user.id}/failed"
                    try:
                        async with session() as db:
                            with pytest.raises(RuntimeError, match="job insert failed"):
                                await profile_image.complete_profile_upload(db, user=user, object_key=failed_key, bucket="test-bucket", original_name="failed.png")
                            await db.rollback()
                    finally:
                        event.remove(ImageProcessingJob, "before_insert", fail_job)
                    async with session() as db:
                        assert await db.scalar(select(StoredObject).where(StoredObject.object_key == failed_key)) is None
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()
    asyncio.run(exercise())


@pytest.mark.skipif(os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires local PostgreSQL")
def test_worker_processes_profile_job_with_mock_storage(monkeypatch):
    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                outer = await connection.begin()
                task = None
                try:
                    def session():
                        return AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
                    monkeypatch.setattr(image_worker, "async_session_factory", session)
                    monkeypatch.setattr(image_worker, "POLL_SECONDS", 0.01)
                    pixels = io.BytesIO()
                    PillowImage.new("RGB", (20, 10), "red").save(pixels, format="PNG")

                    class Storage:
                        outputs = []
                        async def get_object_bytes(self, *_):
                            return pixels.getvalue()
                        async def put_object_bytes(self, bucket, key, data, mime):
                            self.outputs.append((bucket, key, data, mime))

                    storage = Storage()
                    monkeypatch.setattr(image_processing, "get_storage_provider", lambda: storage)
                    owner, image_id, stored_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
                    async with session() as db:
                        db.add_all([
                            StoredObject(id=stored_id, bucket="test", object_key=f"private/profiles/{owner}/image", visibility="private", processing_status="pending"),
                            ProfileImage(id=image_id, owner_id=owner, stored_object_id=stored_id),
                            ImageProcessingJob(kind="profile", image_id=image_id),
                        ])
                        await db.commit()
                    finished = asyncio.Event()
                    original_finish = image_worker._finish
                    async def finish(*args):
                        await original_finish(*args)
                        finished.set()
                    monkeypatch.setattr(image_worker, "_finish", finish)
                    task = asyncio.create_task(image_worker._worker(0))
                    await asyncio.wait_for(finished.wait(), 5)
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    task = None
                    async with session() as db:
                        job = await db.scalar(select(ImageProcessingJob).where(ImageProcessingJob.image_id == image_id))
                        stored = await db.get(StoredObject, stored_id)
                        image = await db.get(ProfileImage, image_id)
                        assert job.status == "done" and stored.processing_status == "ready"
                        assert (image.width, image.height) == (20, 10)
                        assert len(storage.outputs) == 1 and storage.outputs[0][3] == "image/webp"
                finally:
                    if task:
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
                    await outer.rollback()
        finally:
            await engine.dispose()
    asyncio.run(exercise())
