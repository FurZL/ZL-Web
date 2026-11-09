"""Redis 连接与工具。

Redis 仅用于缓存/限流/验证码等可重建或带 TTL 的状态，不作为唯一业务数据源。
"""

from __future__ import annotations

from redis.asyncio import Redis as AsyncRedis

from app.core.config import settings

redis: AsyncRedis = AsyncRedis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> AsyncRedis:
    """FastAPI 依赖：返回全局 Redis 客户端。"""
    return redis


async def close_redis() -> None:
    await redis.aclose()