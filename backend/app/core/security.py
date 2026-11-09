"""安全相关：密码哈希、令牌生成、验证码哈希。

- 密码使用 Argon2id（优先）或 bcrypt，不自行设计算法。
- 验证码只保存哈希，不保存明文。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from app.core.config import settings


def _hash_argon2(secret: str) -> str:
    try:
        from argon2 import PasswordHasher
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("argon2-cffi 未安装") from exc

    ph = PasswordHasher()
    return ph.hash(secret)


def _verify_argon2(secret: str, hashed: str) -> bool:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    ph = PasswordHasher()
    try:
        return ph.verify(hashed, secret)
    except VerifyMismatchError:
        return False


def _hash_bcrypt(secret: str) -> str:
    import bcrypt

    return bcrypt.hashpw(secret.encode(), bcrypt.gensalt()).decode()


def _verify_bcrypt(secret: str, hashed: str) -> bool:
    import bcrypt

    return bcrypt.checkpw(secret.encode(), hashed.encode())


def hash_password(password: str) -> str:
    if settings.password_hash_scheme == "bcrypt":
        return _hash_bcrypt(password)
    return _hash_argon2(password)


def verify_password(password: str, hashed: str) -> bool:
    if hashed.startswith("$2"):
        return _verify_bcrypt(password, hashed)
    return _verify_argon2(password, hashed)


def generate_token(nbytes: int = 32) -> str:
    """生成 URL 安全的随机令牌（Refresh Token / CSRF Token 等）。"""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """令牌只存哈希，防止数据库泄露后被冒用。"""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_code(code: str) -> str:
    """验证码只存哈希。使用带密钥的 HMAC-SHA256。"""
    return hmac.new(
        settings.secret_key.encode(), code.encode(), hashlib.sha256
    ).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)