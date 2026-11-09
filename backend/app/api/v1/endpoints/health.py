"""健康检查端点。

只返回状态，不泄露密钥、连接串或内部信息。
另有 /ready 检查数据库与 Redis。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(redis=Depends(get_redis)) -> dict:
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"status": "ready" if redis_ok else "degraded", "redis": redis_ok}