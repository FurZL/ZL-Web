"""配置 COS 桶 public/ 前缀公有读（Bucket Policy）。

测试阶段让公开图片可被 <img> 直接访问；private/ 前缀保持私有。
生产接 CDN 后此策略可保留（符合「公开前缀公有读，桶默认私有」的设计）。
用法：python scripts/setup_cos_public_read.py
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

from app.providers.factory import get_storage_provider


def main() -> None:
    storage = get_storage_provider()
    bucket = storage.bucket
    region = storage.region
    client = storage._client()

    # APPID 从桶名后缀解析；uid 字段精确保留给腾讯云，尝试用 APPID 作为账号 uid
    appid = bucket.rsplit("-", 1)[-1]

    policy = {
        "version": "2.0",
        "statement": [
            {
                "principal": {"qcs": ["qcs::cam::anyone:anyone"]},
                "effect": "allow",
                "action": ["name/cos:GetObject"],
                "resource": [
                    f"qcs::cos:{region}:uid/{appid}:{bucket}/public/*"
                ],
            }
        ],
    }

    try:
        client.put_bucket_policy(
            Bucket=bucket,
            Policy=json.dumps(policy, ensure_ascii=False),
        )
        print(f"[OK] Bucket Policy 已写入 {bucket}")
        print(f"     允许 anyone 读取 public/* 前缀")
    except Exception as exc:
        print(f"[FAIL] 写入 Policy 失败: {exc}")
        raise


if __name__ == "__main__":
    main()