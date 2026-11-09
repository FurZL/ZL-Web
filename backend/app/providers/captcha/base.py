"""验证码（人机验证）Provider 抽象。

区分：
- 邮件/短信 OTP 发送网关：见 email / sms Provider。
- 人机验证：判断请求是否由真实用户发起。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CaptchaProvider(ABC):
    """云服务商验证码（图形/滑块等）。"""

    @abstractmethod
    async def verify(self, token: str, remote_ip: str | None = None) -> bool:
        ...


class NoopCaptchaProvider(CaptchaProvider):
    """开发占位：一律通过（生产必须关闭）。"""

    async def verify(self, token: str, remote_ip: str | None = None) -> bool:
        return True