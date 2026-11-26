import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.endpoints.auth import _check_cookie_origin
from app.core.config import settings
from app.core.security import hash_token
from app.models.user import User, UserSession
from app.services.auth import AuthError, refresh_tokens


def test_cookie_origin_requires_trusted_origin_or_referer():
    def request(headers):
        return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})
    origin = settings.cors_origins[0].encode()
    _check_cookie_origin(request([(b"origin", origin)]))
    _check_cookie_origin(request([(b"referer", origin + b"/profile")]))
    for headers in ([], [(b"origin", b"https://attacker.example")],
                    [(b"origin", b"null")], [(b"origin", b"https://attacker.example"), (b"referer", origin)]):
        with pytest.raises(HTTPException) as exc:
            _check_cookie_origin(request(headers))
        assert exc.value.status_code == 403


@pytest.mark.skipif(os.environ.get("MEAL_TEST_LOCAL_DB") != "1", reason="requires local PostgreSQL")
def test_replayed_refresh_revokes_only_its_family():
    async def exercise():
        assert make_url(settings.database_url).host in {"localhost", "127.0.0.1", "::1"}
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as connection:
                outer = await connection.begin()
                try:
                    async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                        uid = uuid.uuid4()
                        user = User(id=uid, username=str(uid), display_name="test", email=f"{uid}@example.test", hashed_password="unused", status="active", is_active=True, role="member")
                        first = UserSession(user_id=uid, refresh_token_hash=hash_token("first"), expires_at=datetime.now(timezone.utc) + timedelta(days=1))
                        other = UserSession(user_id=uid, refresh_token_hash=hash_token("other"), expires_at=datetime.now(timezone.utc) + timedelta(days=1))
                        db.add_all([user, first, other])
                        await db.commit()
                        rotated = await refresh_tokens(db, "first")
                        with pytest.raises(AuthError):
                            await refresh_tokens(db, "first")
                        current = await db.scalar(select(UserSession).where(UserSession.refresh_token_hash == hash_token(rotated["refresh_token"])).execution_options(populate_existing=True))
                        assert current.revoked_at is not None
                        assert other.revoked_at is None
                        with pytest.raises(AuthError):
                            await refresh_tokens(db, rotated["refresh_token"])
                        assert (await refresh_tokens(db, "other"))["access_token"]
                finally:
                    await outer.rollback()
        finally:
            await engine.dispose()
    asyncio.run(exercise())
