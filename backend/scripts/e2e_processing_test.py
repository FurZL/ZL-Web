"""图片处理链路端到端验证（真实上传大图，等待 worker 生成派生图）。"""

from __future__ import annotations

import io
import sys
import time

import httpx
from PIL import Image as PILImage

BASE = "http://127.0.0.1:8000/api/v1"


def make_jpeg(w: int, h: int) -> bytes:
    # 渐变测试图，避免全黑无法区分
    img = PILImage.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (x % 256, y % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def main() -> None:
    c = httpx.Client(timeout=60)
    r = c.post(f"{BASE}/auth/login", json={"account": "admin", "password": "admin123456"})
    token = r.json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    data = make_jpeg(2400, 1600)
    print(f"[1] 生成测试图 {len(data)} bytes (2400x1600)")

    r = c.post(
        f"{BASE}/images/upload-intent",
        headers=h,
        json={"filename": "big-test.jpg", "mime_type": "image/jpeg", "size_bytes": len(data), "purpose": "gallery"},
    )
    assert r.status_code == 200, r.text
    intent = r.json()["data"]
    print(f"[2] upload-intent OK, key={intent['object_key']}")

    up = httpx.put(intent["upload_url"], headers={"Content-Type": "image/jpeg"}, content=data, timeout=60)
    assert up.status_code in (200, 204), up.status_code
    print("[3] 直传 COS OK")

    r = c.post(
        f"{BASE}/images/upload-complete",
        headers=h,
        json={"bucket": intent["bucket"], "object_key": intent["object_key"], "purpose": "gallery",
              "original_name": "big-test.jpg", "description": "处理链路测试", "tags": ["测试"]},
    )
    assert r.status_code == 200, r.text
    img = r.json()["data"]
    image_id = img["id"]
    print(f"[4] upload-complete OK, image_id={image_id}, processing={img.get('processing_status')}")

    # 轮询等待 worker 处理完成
    for i in range(20):
        time.sleep(2)
        r = c.get(f"{BASE}/images/")
        items = {x["id"]: x for x in r.json()["data"]["items"]}
        cur = items.get(image_id)
        if cur and cur.get("processing_status") == "ready":
            print(f"[5] 处理完成（等待 {i*2}s）: width={cur['width']} height={cur['height']}")
            print(f"    display_url={cur['display_url']}")
            print(f"    thumb_url={cur['thumb_url']}")
            # 验证派生图可访问
            for label, u in [("display", cur["display_url"]), ("thumb", cur["thumb_url"])]:
                r2 = httpx.get(u, timeout=30, follow_redirects=True)
                print(f"    {label} HTTP {r2.status_code}, size={len(r2.content)} bytes, type={r2.headers.get('content-type')}")
                assert r2.status_code == 200
            print("\n=== 图片处理链路端到端通过 ===")
            return
    print("处理超时，仍未 ready")


if __name__ == "__main__":
    main()