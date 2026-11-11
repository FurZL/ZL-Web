"""创建或初始化一个管理员账号。

用法：
    python scripts/create_admin.py <username> <password> [email]
    python scripts/create_admin.py <username> <password> [email] --reset-password

账号已存在时，默认只确保它是启用状态的管理员，不会覆盖密码。
需要重置已有账号密码时，必须显式传入 ``--reset-password``。
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password, verify_password
from app.models.user import User


async def main(
    username: str,
    password: str,
    email: str,
    *,
    reset_password: bool = False,
) -> None:
    async with async_session_factory() as db:
        existing = await db.scalar(select(User).where(User.username == username))
        if existing:
            changed = []
            if existing.role != "admin":
                existing.role = "admin"
                changed.append("role=admin")
            if existing.status != "active":
                existing.status = "active"
                changed.append("status=active")
            if not existing.is_active:
                existing.is_active = True
                changed.append("is_active=true")
            if reset_password:
                existing.hashed_password = hash_password(password)
                changed.append("password reset")
            elif not verify_password(password, existing.hashed_password):
                await db.rollback()
                print(
                    f"User {username} already exists, but the supplied password "
                    "does not match. Re-run with --reset-password to replace it."
                )
                return

            await db.commit()
            if changed:
                print(f"Admin {username} initialized: " + ", ".join(changed))
            else:
                print(f"Admin {username} already exists; no changes were needed")
            return

        user = User(
            username=username,
            display_name="管理员",
            email=email,
            phone_e164=None,
            hashed_password=hash_password(password),
            role="admin",
            status="active",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"Admin {username} created (email={email})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python scripts/create_admin.py <username> <password> [email]"
            " [--reset-password]"
        )
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]
    positional = [arg for arg in sys.argv[3:] if arg != "--reset-password"]
    email = positional[0] if positional else f"{username}@zjut.edu.cn"
    reset_password = "--reset-password" in sys.argv[3:]
    asyncio.run(
        main(username, password, email, reset_password=reset_password)
    )
