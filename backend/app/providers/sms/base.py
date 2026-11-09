"""短信 Provider 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class SmsProvider(ABC):
    @abstractmethod
    async def send_code(self, phone: str, template: str, variables: dict) -> str:
        """发送短信验证码，返回供应商消息 ID。"""


class LogSmsProvider(SmsProvider):
    """开发占位：仅记录，不真正发送。"""

    async def send_code(self, phone: str, template: str, variables: dict) -> str:
        import logging

        logging.getLogger(__name__).info(
            "SMS (no-op) phone=%s template=%s", phone, template
        )
        return "noop"