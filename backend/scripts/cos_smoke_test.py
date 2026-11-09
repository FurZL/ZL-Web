"""COS 连通性与预签名链路冒烟测试（会真实访问 COS，写入后即删除）。"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")

from app.core.config import settings
from app.providers.storage.cos import CosStorageProvider


def main() -> None:
    p = CosStorageProvider()
    assert p.configured, "COS 未配置完整"
    print(f"[1] provider configured: bucket={p.bucket}, region={p.region}")

    # 客户端实例化
    client = p._client()
    print("[2] CosS3Client created OK")

    # 尝试列出桶（验证密钥权限）
    try:
        resp = client.list_objects(Bucket=p.bucket, MaxKeys=1)
        print(f"[3] list_objects OK, keys found: {len(resp.get('Contents', []))}")
    except Exception as exc:
        print(f"[3] list_objects FAILED: {exc}")
        raise

    # 生成预签名上传 URL
    test_key = "private/smoke-test/hello.txt"
    up = p.presign_upload(
        bucket=p.bucket,
        object_key=test_key,
        content_type="text/plain",
        max_bytes=1024,
        expires_in=600,
    )
    print(f"[4] presign upload OK, url 前缀: {up.url[:80]}...")

    # 真实 PUT 一个测试对象
    import urllib.request

    data = b"furry-zjut cos smoke test " + str(time.time()).encode()
    req = urllib.request.Request(up.url, data=data, method="PUT")
    req.add_header("Content-Type", "text/plain")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[5] PUT status: {resp.status}")
    except Exception as exc:
        print(f"[5] PUT FAILED: {exc}")
        raise

    # HEAD 校验
    head = p.head_object(p.bucket, test_key)
    print(f"[6] head exists={head.exists} size={head.size_bytes}")

    # 预签名下载 URL
    dl = p.presign_download(p.bucket, test_key, expires_in=600)
    print(f"[7] presign download OK: {dl[:80]}...")

    # GET 验证
    try:
        with urllib.request.urlopen(dl, timeout=15) as resp:
            body = resp.read()
            print(f"[8] GET status={resp.status} body={body!r}")
            assert body == data, "内容不一致"
    except Exception as exc:
        print(f"[8] GET FAILED: {exc}")
        raise

    # 清理
    p.delete_object(p.bucket, test_key)
    print("[9] cleanup delete OK")

    print("=== COS 全链路冒烟测试通过 ===")


if __name__ == "__main__":
    main()