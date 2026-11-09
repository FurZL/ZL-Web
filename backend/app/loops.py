"""自定义事件循环工厂。

uvicorn 0.54 在 Windows 上硬编码使用 ProactorEventLoop，
而 psycopg 异步驱动需要 SelectorEventLoop。通过给 uvicorn 传入
`loop="app.loops:selector_loop_factory"` 覆盖默认行为。

注意：uvicorn 会把这个工厂函数本身当 loop_factory 无参调用，
因此它必须是无参调用即返回 loop 实例。
"""

from __future__ import annotations

import asyncio


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop()