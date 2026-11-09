"""开发辅助：创建（或确保存在）一个管理员账号。

用法：python scripts/create_admin.py <username> <password> [email]

开发环境首次需要管理员才能测试审批流程。
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User


async def main(username: str, password: str, email: str) -> None:
    async with async_session_factory() as db:
        existing = await db.scalar(select(User).where(User.username == username))
        if existing:
            print(f"用户 {username} 已存在，跳过创建")
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
        print(f"管理员 {username} 创建成功（email={email}）")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python scripts/create_admin.py <username> <password> [email]")
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else f"{username}@zjut.edu.cn"
    asyncio.run(main(username, password, email))