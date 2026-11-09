"""认证与 OTP 逻辑单元测试（不依赖真实数据库，测纯函数与 token）。"""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password, verify_password
from app.services import auth as auth_service


def test_password_hash_roundtrip():
    hashed = hash_password("a-strong-password-123")
    assert hashed != "a-strong-password-123"
    assert verify_password("a-strong-password-123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    uid = uuid.uuid4()
    token = auth_service.create_access_token(uid, "member")
    payload = auth_service.decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "member"


def test_phone_normalize():
    assert auth_service._normalize_phone("13800138000") == "+8613800138000"
    assert auth_service._normalize_phone("+86 138-0013-8000") == "+8613800138000"
    assert auth_service._normalize_phone("008613800138000") == "+8613800138000"


def test_refresh_token_high_entropy():
    t1 = auth_service._create_refresh_token()
    t2 = auth_service._create_refresh_token()
    assert t1 != t2
    assert len(t1) > 20