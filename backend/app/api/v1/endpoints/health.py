"""健康检查端点。

只返回状态，不泄露密钥、连接串或内部信息。
另有 /ready 检查数据库与 Redis。
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text

from app.core.database import engine
from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response, redis=Depends(get_redis)) -> dict:
    async def check_redis():
        await redis.ping()

    async def check_database():
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def check(task):
        try:
            await asyncio.wait_for(task(), timeout=3)
            return True
        except Exception:
            return False

    database_ok, redis_ok = await asyncio.gather(check(check_database), check(check_redis))
    if not database_ok or not redis_ok:
        response.status_code = 503
    return {"status": "ready" if database_ok and redis_ok else "degraded", "database": database_ok, "redis": redis_ok}
