"""腾讯云 COS 存储 Provider（官方 SDK cos-python-sdk-v5）。

单桶模式：公开/私有内容靠 object_key 的 public//private/ 前缀隔离。
数据库只存 bucket + object_key。
"""

from __future__ import annotations

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

    @property
    def configured(self) -> bool:
        return bool(self.secret_id and self.secret_key and self.region and self.bucket)

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

    def presign_upload(
        self,
        bucket: str,
        object_key: str,
        content_type: str,
        max_bytes: int,
        expires_in: int = 900,
    ) -> UploadPresign:
        bucket = self._resolve_bucket(bucket)
        try:
            client = self._client()
            url = client.get_presigned_url(
                Method="PUT",
                Bucket=bucket,
                Key=object_key,
                Expired=expires_in,
                Headers={"Content-Type": content_type},
            )
        except Exception as exc:
            raise RuntimeError("生成 COS 上传凭证失败") from exc
        return UploadPresign(
            bucket=bucket,
            object_key=object_key,
            url=url,
            expires_in=expires_in,
        )

    def presign_download(
        self, bucket: str, object_key: str, expires_in: int = 900
    ) -> str:
        bucket = self._resolve_bucket(bucket)
        try:
            client = self._client()
            return client.get_presigned_url(
                Method="GET",
                Bucket=bucket,
                Key=object_key,
                Expired=expires_in,
            )
        except Exception as exc:
            raise RuntimeError("生成 COS 下载凭证失败") from exc

    def head_object(self, bucket: str, object_key: str) -> ObjectHead:
        bucket = self._resolve_bucket(bucket)
        from qcloud_cos.cos_exception import CosServiceError

        try:
            client = self._client()
            resp = client.head_object(Bucket=bucket, Key=object_key)
            return ObjectHead(
                exists=True,
                size_bytes=int(resp.get("Content-Length", 0)) or None,
                content_type=resp.get("Content-Type"),
            )
        except CosServiceError as exc:
            if exc.get_error_code() in ("NoSuchKey", "404", "NoSuchResource"):
                return ObjectHead(exists=False)
            raise

    def delete_object(self, bucket: str, object_key: str) -> None:
        bucket = self._resolve_bucket(bucket)
        self._client().delete_object(Bucket=bucket, Key=object_key)

    def public_url(self, bucket: str, object_key: str) -> str:
        # 公开内容走自定义 CDN 域名；未配置时回退 COS 默认域名。
        if self.public_base and "example.com" not in self.public_base:
            return f"{self.public_base}/{object_key}"
        bucket = self._resolve_bucket(bucket)
        return f"https://{bucket}.cos.{self.region}.myqcloud.com/{object_key}"

    async def get_object_bytes(self, bucket: str, object_key: str) -> bytes:
        bucket = self._resolve_bucket(bucket)
        resp = self._client().get_object(Bucket=bucket, Key=object_key)
        return resp["Body"].get_raw_stream().read()

    async def put_object_bytes(
        self, bucket: str, object_key: str, data: bytes, content_type: str
    ) -> None:
        bucket = self._resolve_bucket(bucket)
        self._client().put_object(
            Bucket=bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )