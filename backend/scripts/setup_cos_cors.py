"""配置 COS 桶 CORS 规则（一次性脚本）。

解决浏览器从 127.0.0.1:5173 直传 COS 时的跨域预检失败（Failed to fetch）。
用法：python scripts/setup_cos_cors.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from app.providers.factory import get_storage_provider


def main() -> None:
    storage = get_storage_provider()
    bucket = storage.bucket
    client = storage._client()

    rule = {
        "AllowedOrigin": [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "https://www.example.com",
        ],
        "AllowedMethod": ["GET", "PUT", "POST", "HEAD"],
        "AllowedHeader": ["*"],
        "ExposeHeader": ["ETag", "x-cos-request-id"],
        "MaxAgeSeconds": 600,
    }

    try:
        client.put_bucket_cors(Bucket=bucket, CORSConfiguration={"CORSRule": [rule]})
        print(f"[OK] CORS 已配置到桶 {bucket}")
    except Exception as exc:
        print(f"[FAIL] 配置 CORS 失败: {exc}")
        raise

    # 验证
    resp = client.get_bucket_cors(Bucket=bucket)
    rules = resp.get("CORSRule", [])
    print(f"[验证] 当前 CORS 规则数: {len(rules)}")
    for r in rules:
        print(f"    origin={r.get('AllowedOrigin')} methods={r.get('AllowedMethod')}")


if __name__ == "__main__":
    main()