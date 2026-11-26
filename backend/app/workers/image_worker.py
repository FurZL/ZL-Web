"""PostgreSQL-backed image processing with bounded retries and leases."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select, update

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.image import Image, ProfileImage, StoredObject
from app.models.image_job import ImageProcessingJob
from app.services.image_processing import process_image, process_profile_image

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
LEASE_SECONDS = 120
HEARTBEAT_SECONDS = 30
POLL_SECONDS = 2
_workers: list[asyncio.Task] = []


def _now():
    return datetime.now(timezone.utc)


async def _claim():
    async with async_session_factory() as db:
        instant = _now()
        job = await db.scalar(select(ImageProcessingJob).where(or_(
            and_(ImageProcessingJob.status == "pending", ImageProcessingJob.next_attempt_at <= instant),
            and_(ImageProcessingJob.status == "processing", ImageProcessingJob.lease_until <= instant),
        )).order_by(ImageProcessingJob.next_attempt_at, ImageProcessingJob.created_at).with_for_update(skip_locked=True).limit(1))
        if job is None:
            return None
        image = await db.get(Image if job.kind == "gallery" else ProfileImage, job.image_id)
        stored = await db.get(StoredObject, image.stored_object_id) if image else None
        if stored is None or stored.processing_status == "ready":
            job.status, job.lease_token, job.lease_until = "done", None, None
            await db.commit()
            return None
        if job.attempts >= MAX_ATTEMPTS:
            job.status, job.lease_token, job.lease_until = "failed", None, None
            stored.processing_status = "failed"
            await db.commit()
            return None
        token = uuid.uuid4()
        job.status, job.lease_token = "processing", token
        job.lease_until = instant + timedelta(seconds=LEASE_SECONDS)
        job.attempts += 1
        result = (job.id, job.kind, job.image_id, token, job.attempts)
        await db.commit()
        return result


async def _renew(job_id, token):
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        try:
            async with async_session_factory() as db:
                result = await db.execute(update(ImageProcessingJob).where(
                    ImageProcessingJob.id == job_id, ImageProcessingJob.status == "processing",
                    ImageProcessingJob.lease_token == token,
                ).values(lease_until=_now() + timedelta(seconds=LEASE_SECONDS)))
                await db.commit()
                if not result.rowcount:
                    return
        except Exception:
            logger.warning("图片任务续租失败 job_id=%s", job_id)


async def _finish(job_id, token, attempts, success):
    async with async_session_factory() as db:
        values = {"status": "done" if success else ("failed" if attempts >= MAX_ATTEMPTS else "pending"),
                  "lease_until": None, "lease_token": None}
        if not success:
            values["next_attempt_at"] = _now() + timedelta(seconds=min(300, 5 * 2 ** (attempts - 1)))
        result = await db.execute(update(ImageProcessingJob).where(
            ImageProcessingJob.id == job_id, ImageProcessingJob.status == "processing",
            ImageProcessingJob.lease_token == token,
        ).values(**values).returning(ImageProcessingJob.kind, ImageProcessingJob.image_id))
        if not success:
            row = result.one_or_none()
            if row:
                image = await db.get(Image if row.kind == "gallery" else ProfileImage, row.image_id)
                stored = await db.get(StoredObject, image.stored_object_id) if image else None
                if stored and stored.processing_status != "ready":
                    stored.processing_status = "failed" if attempts >= MAX_ATTEMPTS else "pending"
        await db.commit()


async def _worker(name: int):
    while True:
        try:
            job = await _claim()
            if job is None:
                await asyncio.sleep(POLL_SECONDS)
                continue
            job_id, kind, image_id, token, attempts = job
            heartbeat = asyncio.create_task(_renew(job_id, token))
            try:
                async with async_session_factory() as db:
                    await (process_image(db, image_id) if kind == "gallery" else process_profile_image(db, image_id))
            except Exception:
                logger.exception("图片任务失败 kind=%s image_id=%s attempt=%s", kind, image_id, attempts)
                await _finish(job_id, token, attempts, False)
            else:
                await _finish(job_id, token, attempts, True)
            finally:
                heartbeat.cancel()
                await asyncio.gather(heartbeat, return_exceptions=True)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("图片 worker %s 暂时不可用", name)
            await asyncio.sleep(POLL_SECONDS)


async def start_workers() -> None:
    if _workers:
        return
    for index in range(max(1, settings.image_worker_concurrency)):
        _workers.append(asyncio.create_task(_worker(index)))


async def stop_workers() -> None:
    for worker in _workers:
        worker.cancel()
    await asyncio.gather(*_workers, return_exceptions=True)
    _workers.clear()
