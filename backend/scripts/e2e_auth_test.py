"""端到端认证流程联调脚本（依赖正在运行的后端）。

流程：管理员登录 → 发邮箱/手机验证码 → 注册 pending 用户 → 管理员审批 → 新用户登录 → /me。
"""

from __future__ import annotations

import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
client = httpx.Client(timeout=20)

step = 0


def log(msg: str) -> None:
    global step
    step += 1
    print(f"[{step}] {msg}")


def main() -> None:
    # 1. 管理员登录
    r = client.post(f"{BASE}/auth/login", json={"account": "admin", "password": "admin123456"})
    assert r.status_code == 200, f"admin login: {r.text}"
    admin_token = r.json()["data"]["access_token"]
    log("管理员登录成功")

    # 2. 发邮箱验证码（dev 模式返回 dev_code）
    email = "testuser@zjut.edu.cn"
    r = client.post(f"{BASE}/auth/verify/email", json={"target": email, "purpose": "register"})
    assert r.status_code == 200, f"send email otp: {r.text}"
    email_code = r.json()["data"]["dev_code"]
    log(f"邮箱验证码已发（dev_code={email_code}）")

    # 3. 发手机验证码
    phone = "+86 13800138000"
    r = client.post(f"{BASE}/auth/verify/phone", json={"target": phone, "purpose": "register"})
    assert r.status_code == 200, f"send phone otp: {r.text}"
    phone_code = r.json()["data"]["dev_code"]
    log(f"手机验证码已发（dev_code={phone_code}）")

    # 4. 注册（普通成员）
    r = client.post(
        f"{BASE}/auth/register",
        json={
            "username": "testuser",
            "display_name": "测试用户",
            "email": email,
            "phone": phone,
            "password": "testpassword123",
            "email_code": email_code,
            "phone_code": phone_code,
        },
    )
    assert r.status_code == 200, f"register: {r.text}"
    log("注册成功，状态 pending")

    # 5. 查 pending 列表（admin）
    r = client.get(f"{BASE}/admin/users/pending", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"list pending: {r.text}"
    users = r.json()["data"]["items"]
    user = next(u for u in users if u["username"] == "testuser")
    log(f"pending 列表查到 testuser（id={user['id']}）")

    # 6. 未审批时登录应被拒
    r = client.post(f"{BASE}/auth/login", json={"account": "testuser", "password": "testpassword123"})
    assert r.status_code == 403, f"pending login should be 403, got {r.status_code}"
    log("未审批登录被正确拒绝（403 PENDING_APPROVAL）")

    # 7. 审批通过
    r = client.post(
        f"{BASE}/admin/users/{user['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, f"approve: {r.text}"
    log("管理员审批通过")

    # 8. 新用户登录
    r = client.post(f"{BASE}/auth/login", json={"account": "testuser", "password": "testpassword123"})
    assert r.status_code == 200, f"user login: {r.text}"
    data = r.json()["data"]
    user_token = data["access_token"]
    refresh_token = data["refresh_token"]
    log("新用户登录成功")

    # 9. /me 验证当前用户
    r = client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200, f"me: {r.text}"
    me = r.json()
    assert me["username"] == "testuser"
    log(f"/me 验证通过（username={me['username']}, role={me['role']}）")

    # 10. 刷新令牌轮换
    r = client.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200, f"refresh: {r.text}"
    refresh_data = r.json()["data"]
    assert refresh_data["refresh_token"] != refresh_token
    log("刷新令牌轮换成功（旧令牌已撤销，签发新令牌）")

    # 11. 复用检测：旧 refresh token 再刷新应失败
    r = client.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401, f"reuse should 401, got {r.status_code}"
    log("旧刷新令牌复用被正确拒绝（401）")

    print("\n=== 端到端认证流程全部通过 ===")


if __name__ == "__main__":
    main()