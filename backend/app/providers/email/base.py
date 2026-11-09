"""邮件 Provider 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmailProvider(ABC):
    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        template: str,
        variables: dict,
    ) -> str:
        """发送邮件，返回供应商消息 ID。"""


class LogEmailProvider(EmailProvider):
    """开发占位：仅记录，不真正发送。"""

    async def send(
        self,
        to: str,
        subject: str,
        template: str,
        variables: dict,
    ) -> str:
        import logging

        logging.getLogger(__name__).info(
            "Email (no-op) to=%s subject=%s template=%s", to, subject, template
        )
        return "noop"