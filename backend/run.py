"""开发/生产启动入口。

uvicorn 0.54 在 Windows 上默认使用 ProactorEventLoop，与 psycopg 异步驱动冲突。
通过传入自定义 loop factory（SelectorEventLoop）解决。

用法：
  python run.py                # 默认 127.0.0.1:8000
  python run.py --reload       # 开发热重载
"""

from __future__ import annotations

import sys

import uvicorn


def main() -> None:
    reload = "--reload" in sys.argv
    kwargs: dict = {
        "host": "127.0.0.1",
        "port": 8000,
        "reload": reload,
        "workers": 1,
    }
    # Windows 上用 SelectorEventLoop 兼容 psycopg
    if sys.platform == "win32":
        kwargs["loop"] = "app.loops:selector_loop_factory"

    uvicorn.run("app.main:app", **kwargs)


if __name__ == "__main__":
    main()