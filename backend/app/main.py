"""FastAPI 应用入口。

模块化单体：按分层约定组织，业务逻辑不堆在 main.py。
生产环境关闭 debug/reload 与公开 API 文档（由部署侧控制）。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, redis
from app.middleware import setup_middleware
from app.workers.image_worker import start_workers, stop_workers


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await start_workers()
    yield
    await stop_workers()
    await close_redis()


def create_app() -> FastAPI:
    docs_kwargs = {}
    if settings.is_production:
        docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        **docs_kwargs,
    )

    # CORS：生产只允许真实前端来源，禁止 * 加 credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-CSRF-Token",
            "X-Request-ID",
            "Idempotency-Key",
        ],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )

    setup_middleware(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()