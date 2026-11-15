"""开发/生产启动入口。

uvicorn 0.54 在 Windows 上默认使用 ProactorEventLoop，与 psycopg 异步驱动冲突。
通过传入自定义 loop factory（SelectorEventLoop）解决。

用法：
  python run.py                     # 默认 127.0.0.1:8000
  python run.py --host 0.0.0.0      # 监听所有接口
  python run.py --reload            # 开发热重载
"""

from __future__ import annotations

import argparse
import sys

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    kwargs: dict = {
        "host": args.host,
        "port": 8000,
        "reload": args.reload,
        "workers": 1,
    }
    # Windows 上用 SelectorEventLoop 兼容 psycopg
    if sys.platform == "win32":
        kwargs["loop"] = "app.loops:selector_loop_factory"

    uvicorn.run("app.main:app", **kwargs)


if __name__ == "__main__":
    main()