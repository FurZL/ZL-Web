"""腾讯云 COS 存储 Provider（官方 SDK cos-python-sdk-v5）。

单桶模式：公开/私有内容靠 object_key 的 public/private/ 前缀隔离。
数据库只存 bucket + object_key。

COS SDK 是同步阻塞 API，所有方法用 asyncio.to_thread 包装成真正的 async，
避免阻塞 FastAPI 事件循环。

Dev prefix：
  多人共用同一 Bucket 时通过 COS_DEV_PREFIX 透明隔离。数据库存储逻辑 key（不含前缀），
  Provider 与 COS 交互时自动在前面追加 dev prefix。
  例如 COS_DEV_PREFIX=dev-alice，逻辑 key public/gallery/original/2026/11/abc
    → 物理 key dev-alice/public/gallery/original/2026/11/abc。
  生产环境不设 COS_DEV_PREFIX，逻辑 key 即物理 key。
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.providers.storage.base import (
    ObjectHead,
    StorageProvider,
    UploadPresign,
)


class CosStorageProvider(StorageProvider):
    def __init__(self) -> None:
        self.secret_id = settings.cos_secret_id
        self.secret_key = settings.cos_secret_key
        self.region = settings.cos_region
        self.bucket = settings.cos_bucket
        self.public_base = settings.public_asset_base_url.rstrip("/")
        self._dev_prefix_raw = settings.cos_dev_prefix.strip("/")

    @property
    def configured(self) -> bool:
        return bool(self.secret_id and self.secret_key and self.region and self.bucket)

    # ------------------------------------------------------------------
    # Dev prefix
    # ------------------------------------------------------------------

    @property
    def _dev_prefix(self) -> str:
        return f"{self._dev_prefix_raw}/" if self._dev_prefix_raw else ""

    def _phys_key(self, logical_key: str) -> str:
        """逻辑 key → 物理 key（挂 dev prefix）。"""
        return f"{self._dev_prefix}{logical_key}"

    # ------------------------------------------------------------------
    # SDK helpers
    # ------------------------------------------------------------------

    def _client(self):
        if not self.configured:
            raise RuntimeError("COS 未配置 SecretId/SecretKey/Region/Bucket")
        from qcloud_cos import CosConfig, CosS3Client

        config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key,
            Scheme="https",
        )
        return CosS3Client(config)


    def _resolve_bucket(self, bucket: str | None) -> str:
        resolved = bucket or self.bucket
        if not resolved:
            raise RuntimeError("未配置 COS Bucket")
        return resolved

    # ------------------------------------------------------------------
    # StorageProvider interface – all use _phys_key for COS I/O
    # ------------------------------------------------------------------

    async def presign_upload(
        self,
        bucket: str,
        object_key: str,
        content_type: str,
        max_bytes: int,
        expires_in: int = 900,
    ) -> UploadPresign:
        bucket = self._resolve_bucket(bucket)
        phys_key = self._phys_key(object_key)

        def _do() -> str:
            client = self._client()
            return client.get_presigned_url(
                Method="PUT",
                Bucket=bucket,
                Key=phys_key,
                Expired=expires_in,
                Headers={"Content-Type": content_type},
            )

        try:
            url = await asyncio.to_thread(_do)
        except Exception as exc:
            raise RuntimeError("生成 COS 上传凭证失败") from exc
        return UploadPresign(
            bucket=bucket,
            object_key=object_key,
            url=url,
            expires_in=expires_in,
        )

    async def presign_download(
        self, bucket: str, object_key: str, expires_in: int = 900
    ) -> str:
        bucket = self._resolve_bucket(bucket)
        phys_key = self._phys_key(object_key)

        def _do() -> str:
            client = self._client()
            return client.get_presigned_url(
                Method="GET",
                Bucket=bucket,
                Key=phys_key,
                Expired=expires_in,
            )

        try:
            return await asyncio.to_thread(_do)
        except Exception as exc:
            raise RuntimeError("生成 COS 下载凭证失败") from exc

    async def head_object(self, bucket: str, object_key: str) -> ObjectHead:
        bucket = self._resolve_bucket(bucket)
        phys_key = self._phys_key(object_key)

        def _do() -> ObjectHead:
            from qcloud_cos.cos_exception import CosServiceError

            client = self._client()
            try:
                resp = client.head_object(Bucket=bucket, Key=phys_key)
                return ObjectHead(
                    exists=True,
                    size_bytes=int(resp.get("Content-Length", 0)) or None,
                    content_type=resp.get("Content-Type"),
                )
            except CosServiceError as exc:
                if exc.get_error_code() in ("NoSuchKey", "404", "NoSuchResource"):
                    return ObjectHead(exists=False)
                raise

        return await asyncio.to_thread(_do)

    async def delete_object(self, bucket: str, object_key: str) -> None:
        bucket = self._resolve_bucket(bucket)
        phys_key = self._phys_key(object_key)

        def _do() -> None:
            self._client().delete_object(Bucket=bucket, Key=phys_key)

        await asyncio.to_thread(_do)

    def public_url(self, bucket: str, object_key: str) -> str:
        # 公开内容走自定义 CDN 域名；未配置时回退 COS 默认域名。
        # 物理 key 前缀体现在 URL 路径中（没有 CDN 重写规则时 URL 直接映射 COS 路径）。
        phys_key = self._phys_key(object_key)
        if self.public_base and "example.com" not in self.public_base:
            return f"{self.public_base}/{phys_key}"
        bucket = self._resolve_bucket(bucket)
        return f"https://{bucket}.cos.{self.region}.myqcloud.com/{phys_key}"

    async def get_object_bytes(self, bucket: str, object_key: str) -> bytes:
        bucket = self._resolve_bucket(bucket)
        phys_key = self._phys_key(object_key)

        def _do() -> bytes:
            resp = self._client().get_object(Bucket=bucket, Key=phys_key)
            return resp["Body"].get_raw_stream().read()

        return await asyncio.to_thread(_do)

    async def put_object_bytes(
        self, bucket: str, object_key: str, data: bytes, content_type: str
    ) -> None:
        bucket = self._resolve_bucket(bucket)
        phys_key = self._phys_key(object_key)

        def _do() -> None:
            self._client().put_object(
                Bucket=bucket,
                Key=phys_key,
                Body=data,
                ContentType=content_type,
                CacheControl=("private, no-store" if object_key.startswith("private/") else "public, max-age=31536000, immutable"),
            )

        await asyncio.to_thread(_do)
