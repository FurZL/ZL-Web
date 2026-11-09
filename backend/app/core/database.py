"""数据库引擎与会话管理。

SQLAlchemy 2.x 异步引擎；连接池保持小规模，适配 2C2G 单 Worker 部署。
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncGenerator

# Windows 上 psycopg 异步模式不能用默认的 ProactorEventLoop，
# 需在创建事件循环前设置 SelectorEventLoop 策略。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：每个请求一个会话。"""
    async with async_session_factory() as session:
        yield session