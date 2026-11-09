"""私有相册端到端测试（上传→列表→签名URL→缩略图→删除）。"""

from __future__ import annotations

import time

import httpx

BASE = "http://127.0.0.1:8000/api/v1"

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff1f0005000101c1a8bf0000000049454e44ae426082"
)


def main() -> None:
    c = httpx.Client(timeout=30)

    # admin 登录
    r = c.post(f"{BASE}/auth/login", json={"account": "admin", "password": "admin123456"})
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    print("[1] 登录成功")

    # 私有上传 intent
    r = c.post(
        f"{BASE}/profile/me/images/upload-intent",
        headers=h,
        json={"filename": "private-test.png", "mime_type": "image/png", "size_bytes": len(PNG_1PX)},
    )
    assert r.status_code == 200, r.text
    intent = r.json()["data"]
    print(f"[2] 私有上传凭证 OK, key={intent['object_key']}")
    assert intent["visibility"] == "private"
    assert intent["object_key"].startswith("private/profiles/")

    # 直传 COS
    up = httpx.put(intent["upload_url"], headers={"Content-Type": "image/png"}, content=PNG_1PX, timeout=30)
    assert up.status_code in (200, 204), up.status_code
    print("[3] 直传 COS OK")

    # upload-complete
    r = c.post(
        f"{BASE}/profile/me/images/upload-complete",
        headers=h,
        json={"bucket": intent["bucket"], "object_key": intent["object_key"], "original_name": "private-test.png", "description": "私有测试图"},
    )
    assert r.status_code == 200, r.text
    pid = r.json()["data"]["id"]
    print(f"[4] 落库 OK, id={pid}")

    # 等 worker 处理缩略图
    time.sleep(3)

    # 列表
    r = c.get(f"{BASE}/profile/me/images", headers=h)
    assert r.status_code == 200, r.text
    items = r.json()["data"]["items"]
    my = next((x for x in items if x["id"] == pid), None)
    assert my is not None, "列表未找到私有图"
    print(f"[5] 列表找到私有图, thumb={'有' if my['thumb_url'] else '无'}, status={my['processing_status']}")

    # 签名 URL（原图）
    r = c.get(f"{BASE}/profile/me/images/{pid}/url", headers=h)
    assert r.status_code == 200, r.text
    signed = r.json()["data"]["url"]
    print(f"[6] 原图签名 URL 生成 OK: {signed[:80]}...")

    # 缩略图签名 URL 可访问
    if my["thumb_url"]:
        r = httpx.get(my["thumb_url"], timeout=20)
        print(f"[7] 缩略图签名 URL 访问: {r.status_code}")
        assert r.status_code == 200

    # 删除
    r = c.delete(f"{BASE}/profile/me/images/{pid}", headers=h)
    assert r.status_code == 200, r.text
    print("[8] 删除成功")

    # 列表确认已删
    r = c.get(f"{BASE}/profile/me/images", headers=h)
    items = r.json()["data"]["items"]
    assert all(x["id"] != pid for x in items)
    print("[9] 确认已从列表移除")

    print("\n=== 私有相册端到端通过 ===")


if __name__ == "__main__":
    main()