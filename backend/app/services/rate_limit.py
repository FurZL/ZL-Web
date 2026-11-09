"""限流服务：基于 Redis 的分布式计数器。"""

from __future__ import annotations

import time

from redis.asyncio import Redis


class RateLimiter:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """滑动窗口近似：按固定窗口计数。"""
        bucket = int(time.time() // window_seconds)
        rkey = f"ratelimit:{key}:{bucket}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(rkey)
            pipe.expire(rkey, window_seconds * 2)
            count, _ = await pipe.execute()
        return int(count) <= limit