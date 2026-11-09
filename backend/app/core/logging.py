"""结构化日志与敏感信息脱敏。

不记录密码、OTP、Cookie、Authorization、Refresh Token、完整签名 URL、Secret。
"""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "access_key",
    "refresh_token",
    "code",
    "signature",
    "x-amz-signature",
    "session",
}


class MaskingFilter(logging.Filter):
    """对格式化后的日志记录做 key 级脱敏。"""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        lowered = message.lower()
        for key in _SENSITIVE_KEYS:
            if key in lowered:
                # 简单策略：整体降级为脱敏提示，避免半脱敏泄露。
                record.msg = "<redacted: potentially sensitive content>"
                record.args = ()
                break
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
    )
    handler.addFilter(MaskingFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # 降低第三方库噪音
    logging.getLogger("uvicorn.access").setLevel(
        logging.WARNING if not settings.debug else logging.INFO
    )