"""OTP 验证码服务：生成、发送、校验。

- 验证码只存哈希，不存明文。
- 短时效、单次使用、用途隔离、失败次数限制。
- 开发模式（OTP_DEV_MODE=true）：不调用真实 Provider，验证码返回在响应里，方便联调。
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import constant_time_equal, hash_code, hash_token


def _normalize_target(target: str) -> str:
    """统一目标字符串（邮箱转小写；手机号去空格）。"""
    t = target.strip()
    if "@" in t:
        return t.lower()
    return t


def _target_channel(target: str) -> str:
    return "email" if "@" in target else "sms"


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


class OtpError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


async def send_otp(
    db: AsyncSession,
    target: str,
    purpose: str,
) -> dict:
    """生成验证码、持久化哈希、发送；返回发送结果。"""
    from app.models.user import VerificationChallenge

    target = _normalize_target(target)
    channel = _target_channel(target)
    code = _generate_code()
    now = datetime.now(timezone.utc)

    # 作废该 target+purpose 下未消费的旧验证码
    pending = await db.scalars(
        select(VerificationChallenge).where(
            VerificationChallenge.target_hash == hash_token(target),
            VerificationChallenge.purpose == purpose,
            VerificationChallenge.status == "pending",
        )
    )
    for old in pending:
        old.status = "expired"

    challenge = VerificationChallenge(
        target_hash=hash_token(target),
        purpose=purpose,
        channel=channel,
        code_hash=hash_code(code),
        provider=settings.email_provider or settings.sms_provider or "dev",
        status="pending",
        attempts=0,
        expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
    )
    db.add(challenge)
    await db.commit()

    # 发送
    if settings.otp_dev_mode:
        sent_by = "dev"
    else:
        if channel == "email":
            from app.providers.factory import get_email_provider

            await get_email_provider().send(
                to=target,
                subject=f"【{settings.app_name}】验证码",
                template="otp",
                variables={"code": code, "purpose": purpose, "ttl_minutes": settings.otp_ttl_seconds // 60},
            )
            sent_by = "email"
        else:
            from app.providers.factory import get_sms_provider

            await get_sms_provider().send_code(
                phone=target,
                template="otp",
                variables={"code": code},
            )
            sent_by = "sms"

    result: dict = {"sent": True, "channel": channel, "expires_in": settings.otp_ttl_seconds}
    if settings.otp_dev_mode:
        result["dev_code"] = code
    return result


async def verify_otp(
    db: AsyncSession,
    target: str,
    purpose: str,
    code: str,
) -> None:
    """校验验证码，成功则标记消费；失败抛 OtpError。"""
    from app.models.user import VerificationChallenge

    target = _normalize_target(target)
    now = datetime.now(timezone.utc)

    # 取最新的 pending 挑战
    challenge = (
        await db.scalars(
            select(VerificationChallenge)
            .where(
                VerificationChallenge.target_hash == hash_token(target),
                VerificationChallenge.purpose == purpose,
                VerificationChallenge.status == "pending",
            )
            .order_by(VerificationChallenge.created_at.desc())
        )
    ).first()

    if challenge is None:
        raise OtpError("CODE_NOT_FOUND", "验证码不存在或已失效，请重新发送")

    if challenge.expires_at < now:
        challenge.status = "expired"
        await db.commit()
        raise OtpError("CODE_EXPIRED", "验证码已过期，请重新发送")

    if challenge.attempts >= settings.otp_max_attempts:
        challenge.status = "expired"
        await db.commit()
        raise OtpError("TOO_MANY_ATTEMPTS", "尝试次数过多，请重新发送验证码")

    if not constant_time_equal(challenge.code_hash, hash_code(code)):
        challenge.attempts += 1
        await db.commit()
        raise OtpError("CODE_INVALID", "验证码错误")

    challenge.status = "consumed"
    challenge.consumed_at = now
    await db.commit()