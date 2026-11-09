"""人机验证 Provider 抽象（Bot 检测）。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class HumanVerificationProvider(ABC):
    @abstractmethod
    async def verify(self, token: str, remote_ip: str | None = None) -> bool:
        ...


class NoopHumanVerificationProvider(HumanVerificationProvider):
    """开发占位：一律通过（生产必须关闭）。"""

    async def verify(self, token: str, remote_ip: str | None = None) -> bool:
        return True