"""私有相册端到端测试（用正常尺寸图，验证缩略图生成的完整链路）。"""

from __future__ import annotations

import io
import time

import httpx
from PIL import Image as PILImage

BASE = "http://127.0.0.1:8000/api/v1"


def make_jpeg(w: int, h: int) -> bytes:
    img = PILImage.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (x % 256, y % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def main() -> None:
    c = httpx.Client(timeout=30)
    r = c.post(f"{BASE}/auth/login", json={"account": "admin", "password": "admin123456"})
    token = r.json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    data = make_jpeg(1200, 800)
    print(f"[1] 测试图 {len(data)} bytes (1200x800)")

    r = c.post(
        f"{BASE}/profile/me/images/upload-intent",
        headers=h,
        json={"filename": "private-real.jpg", "mime_type": "image/jpeg", "size_bytes": len(data)},
    )
    assert r.status_code == 200, r.text
    intent = r.json()["data"]
    print(f"[2] 上传凭证 OK, visibility={intent['visibility']}")

    httpx.put(intent["upload_url"], headers={"Content-Type": "image/jpeg"}, content=data, timeout=30)
    print("[3] 直传 OK")

    r = c.post(
        f"{BASE}/profile/me/images/upload-complete",
        headers=h,
        json={"bucket": intent["bucket"], "object_key": intent["object_key"], "original_name": "private-real.jpg", "description": "真实私有图"},
    )
    assert r.status_code == 200, r.text
    pid = r.json()["data"]["id"]
    print(f"[4] 落库 OK id={pid}")

    # 等待 worker 处理
    for i in range(10):
        time.sleep(2)
        r = c.get(f"{BASE}/profile/me/images", headers=h)
        items = r.json()["data"]["items"]
        cur = next((x for x in items if x["id"] == pid), None)
        if cur and cur["processing_status"] == "ready":
            print(f"[5] 缩略图生成 OK（等待 {i*2}s）: width={cur['width']} height={cur['height']}")
            print(f"    thumb_url={cur['thumb_url'][:90]}...")
            # 签名 URL 可访问
            r2 = httpx.get(cur["thumb_url"], timeout=20)
            print(f"    缩略图访问: {r2.status_code}")
            assert r2.status_code == 200
            break
        if cur and cur["processing_status"] == "failed":
            print("[FAIL] 处理失败")
            return
    else:
        print("[FAIL] 处理超时")
        return

    # 原图签名 URL
    r = c.get(f"{BASE}/profile/me/images/{pid}/url", headers=h)
    assert r.status_code == 200, r.text
    print("[6] 原图签名 URL OK")

    # 删除清理
    r = c.delete(f"{BASE}/profile/me/images/{pid}", headers=h)
    assert r.status_code == 200
    print("[7] 删除清理 OK")

    print("\n=== 私有相册完整链路通过 ===")


if __name__ == "__main__":
    main()