"""人机验证端点 — 滑块拼图验证码。

GET  /captcha/challenge → {token, gap_x}
POST /captcha/verify     → {success, verification_token}

验证通过后返回短时效 verification_token，
调用 OTP 发送接口时需附带此 token 以证明通过了人机验证。
"""

from __future__ import annotations

import secrets
import hashlib
import hmac
from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.response import ok
from app.core.config import settings
from app.core.redis import redis

router = APIRouter(prefix="/captcha", tags=["captcha"])

CAPTCHA_TTL = timedelta(seconds=120)
VERIFY_TTL = timedelta(seconds=300)
TOLERANCE = 6  # 允许 ±6px 误差


def _make_token() -> str:
    return secrets.token_urlsafe(24)


def _captcha_key(token: str) -> str:
    return f"captcha:{token}"


def _verify_key(token: str) -> str:
    return f"captcha_verified:{token}"


@router.get("/challenge")
async def get_challenge():
    """生成一次滑块验证挑战。返回 token 和缺口 x 坐标（后端存储，不返回前端）。"""
    token = _make_token()
    gap_x = secrets.randbelow(180) + 40  # 40 ~ 219 (x 范围)
    gap_y = secrets.randbelow(60) + 20  # 20 ~ 79 (y 范围)
    await redis.set(_captcha_key(token), str(gap_x) + "," + str(gap_y), ex=CAPTCHA_TTL)
    return ok({"token": token, "gap_x": int(gap_x), "gap_y": int(gap_y), "expires_in": int(CAPTCHA_TTL.total_seconds())})


class VerifyRequest(BaseModel):
    token: str
    x: int  # 用户滑动到的 x 坐标


@router.post("/verify")
async def verify_captcha(body: VerifyRequest):
    stored = await redis.get(_captcha_key(body.token))
    if stored is None:
        raise HTTPException(status_code=400, detail={"code": "CAPTCHA_EXPIRED", "message": "验证已过期，请刷新重试"})

    gap_x = int(stored.split(",")[0])
    if abs(body.x - gap_x) > TOLERANCE:
        await redis.delete(_captcha_key(body.token))
        raise HTTPException(status_code=400, detail={"code": "CAPTCHA_FAILED", "message": "验证失败，请重试"})

    await redis.delete(_captcha_key(body.token))
    verify_token = _make_token()
    await redis.set(_verify_key(verify_token), "1", ex=VERIFY_TTL)
    return ok({"verification_token": verify_token, "expires_in": int(VERIFY_TTL.total_seconds())})


async def check_verification_token(token: str) -> bool:
    """校验人机验证 token，成功则消耗掉（一次性）。"""
    if not token:
        return False
    key = _verify_key(token)
    exists = await redis.get(key)
    if exists:
        await redis.delete(key)
        return True
    return False
