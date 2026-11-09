"""验证 COS CORS 是否对浏览器直传生效（模拟浏览器预检 + 直传）。"""

from __future__ import annotations

import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
ORIGIN = "http://127.0.0.1:5173"

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff1f0005000101c1a8bf0000000049454e44ae426082"
)


def main() -> None:
    c = httpx.Client(timeout=30)
    r = c.post(f"{BASE}/auth/login", json={"account": "admin", "password": "admin123456"})
    token = r.json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = c.post(
        f"{BASE}/images/upload-intent",
        headers=h,
        json={"filename": "cors.png", "mime_type": "image/png", "size_bytes": len(PNG_1PX), "purpose": "gallery"},
    )
    intent = r.json()["data"]
    url = intent["upload_url"]

    # 模拟浏览器预检 OPTIONS
    preflight = httpx.options(
        url,
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=20,
    )
    print(f"[预检] OPTIONS status={preflight.status_code}")
    print(f"       allow-origin: {preflight.headers.get('access-control-allow-origin')}")
    print(f"       allow-methods: {preflight.headers.get('access-control-allow-methods')}")

    # 模拟浏览器带 Origin 直传
    up = httpx.put(
        url,
        headers={"Content-Type": "image/png", "Origin": ORIGIN},
        content=PNG_1PX,
        timeout=20,
    )
    print(f"[直传] PUT status={up.status_code}")
    print(f"       allow-origin: {up.headers.get('access-control-allow-origin')}")
    print(f"       expose-etag: {up.headers.get('access-control-expose-headers')}")

    assert "5173" in (preflight.headers.get("access-control-allow-origin") or ""), "预检未放行 origin"
    print("\n=== CORS 对浏览器直传已生效 ===")


if __name__ == "__main__":
    main()