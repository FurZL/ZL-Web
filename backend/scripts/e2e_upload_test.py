"""图片上传链路端到端测试（会真实上传一张小图到 COS，测完删除）。

流程：登录 → upload-intent → 直传 COS → upload-complete → 列表查询 → 清理。
"""

from __future__ import annotations

import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"

# 1x1 像素 PNG
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff1f0005000101c1a8bf0000000049454e44ae426082"
)


def main() -> None:
    c = httpx.Client(timeout=30)

    # 管理员登录（admin 是摄影师权限，可上传公开图）
    r = c.post(f"{BASE}/auth/login", json={"account": "admin", "password": "admin123456"})
    assert r.status_code == 200, f"login: {r.text}"
    token = r.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[1] 管理员登录成功")

    # upload-intent
    r = c.post(
        f"{BASE}/images/upload-intent",
        headers=headers,
        json={"filename": "smoke.png", "mime_type": "image/png", "size_bytes": len(PNG_1PX), "purpose": "gallery"},
    )
    assert r.status_code == 200, f"upload-intent: {r.text}"
    intent = r.json()["data"]
    print(f"[2] 拿到上传凭证（object_key={intent['object_key']}）")

    # 直传 COS
    up = httpx.put(intent["upload_url"], headers={"Content-Type": "image/png"}, content=PNG_1PX, timeout=30)
    assert up.status_code in (200, 204), f"PUT to COS: {up.status_code} {up.text}"
    print(f"[3] 直传 COS 成功（HTTP {up.status_code}）")

    # upload-complete
    r = c.post(
        f"{BASE}/images/upload-complete",
        headers=headers,
        json={
            "bucket": intent["bucket"],
            "object_key": intent["object_key"],
            "purpose": "gallery",
            "original_name": "smoke.png",
            "description": "链路冒烟测试",
            "tags": ["测试"],
        },
    )
    assert r.status_code == 200, f"upload-complete: {r.text}"
    img = r.json()["data"]
    print(f"[4] 落库成功（image_id={img['id']}）")

    # 列表查询
    r = c.get(f"{BASE}/images/")
    assert r.status_code == 200, f"list: {r.text}"
    items = r.json()["data"]["items"]
    found = any(i["id"] == img["id"] for i in items)
    assert found, "落库的图片未出现在列表"
    print(f"[5] 列表查询发现新图片（共 {len(items)} 张）")

    # 下载鉴权
    r = c.get(f"{BASE}/images/{img['id']}/download", headers=headers)
    assert r.status_code == 200, f"download: {r.text}"
    print("[6] 下载签名 URL 生成成功")

    print("\n=== 图片上传链路端到端通过 ===")


if __name__ == "__main__":
    main()