"""Provider 工厂：按配置选择具体实现。"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.providers.captcha.base import CaptchaProvider, NoopCaptchaProvider
from app.providers.email.base import EmailProvider, LogEmailProvider
from app.providers.human_verification.base import (
    HumanVerificationProvider,
    NoopHumanVerificationProvider,
)
from app.providers.sms.base import LogSmsProvider, SmsProvider
from app.providers.storage.base import StorageProvider
from app.providers.storage.cos import CosStorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    if settings.storage_provider == "cos":
        return CosStorageProvider()
    raise ValueError(f"未知存储 Provider: {settings.storage_provider}")


@lru_cache
def get_email_provider() -> EmailProvider:
    # 未配置时使用 no-op；配置了 EMAIL_PROVIDER=smtp 时可在此扩展。
    return LogEmailProvider()


@lru_cache
def get_sms_provider() -> SmsProvider:
    return LogSmsProvider()


@lru_cache
def get_captcha_provider() -> CaptchaProvider:
    return NoopCaptchaProvider()


@lru_cache
def get_human_verification_provider() -> HumanVerificationProvider:
    return NoopHumanVerificationProvider()