"""后台图片处理 worker。

轻量编排：asyncio.Queue + 固定数量的串行 worker，不引入 Celery。
由 FastAPI lifespan 启动/停止；upload-complete 时把 image_id 入队。
每个 worker 串行处理单张图，worker 数即并发上限（2C2G 默认 1，可配置）。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.image_processing import process_image, process_profile_image

logger = logging.getLogger(__name__)


@dataclass
class _Job:
    kind: str  # "gallery" | "profile"
    image_id: uuid.UUID


_queue: asyncio.Queue[_Job] = asyncio.Queue()
_workers: list[asyncio.Task] = []
_stop = asyncio.Event()


def enqueue_image(image_id: uuid.UUID) -> None:
    _queue.put_nowait(_Job("gallery", image_id))
    logger.info("公开图处理入队 image_id=%s（队列长度 %s）", image_id, _queue.qsize())


def enqueue_profile_image(image_id: uuid.UUID) -> None:
    _queue.put_nowait(_Job("profile", image_id))
    logger.info("私有图处理入队 image_id=%s（队列长度 %s）", image_id, _queue.qsize())


async def _worker(name: int) -> None:
    logger.info("图片处理 worker %s 启动", name)
    while True:
        try:
            job = await asyncio.wait_for(_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            if _stop.is_set():
                break
            continue

        try:
            async with async_session_factory() as db:
                if job.kind == "gallery":
                    await process_image(db, job.image_id)
                else:
                    await process_profile_image(db, job.image_id)
        except Exception:
            logger.exception("worker %s 处理失败 kind=%s image_id=%s", name, job.kind, job.image_id)
        finally:
            _queue.task_done()

    logger.info("图片处理 worker %s 退出", name)


async def start_workers() -> None:
    _stop.clear()
    count = max(1, settings.image_worker_concurrency)
    for i in range(count):
        _workers.append(asyncio.create_task(_worker(i)))


async def stop_workers() -> None:
    _stop.set()
    for w in _workers:
        w.cancel()
    await asyncio.gather(*_workers, return_exceptions=True)
    _workers.clear()