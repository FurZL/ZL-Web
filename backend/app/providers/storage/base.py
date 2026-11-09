"""对象存储 Provider 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class UploadPresign:
    bucket: str
    object_key: str
    url: str
    expires_in: int


@dataclass
class ObjectHead:
    exists: bool
    size_bytes: int | None = None
    content_type: str | None = None


class StorageProvider(ABC):
    """对象存储的抽象接口。

    数据库只存 bucket + object_key，公开 URL 由后端按当前域名动态生成。
    """

    @abstractmethod
    async def presign_upload(
        self,
        bucket: str,
        object_key: str,
        content_type: str,
        max_bytes: int,
        expires_in: int = 900,
    ) -> UploadPresign:
        """生成短时效、限定 Key/方法/大小的预签名上传 URL。"""

    @abstractmethod
    async def presign_download(
        self, bucket: str, object_key: str, expires_in: int = 900
    ) -> str:
        """生成短时效签名下载 URL（私有文件）。"""

    @abstractmethod
    async def head_object(self, bucket: str, object_key: str) -> ObjectHead:
        """校验对象存在性、大小与类型。"""

    @abstractmethod
    async def delete_object(self, bucket: str, object_key: str) -> None:
        """删除对象（软删除结合清理任务使用）。"""

    @abstractmethod
    def public_url(self, bucket: str, object_key: str) -> str:
        """根据当前域名配置生成公开访问 URL。"""

    async def get_object_bytes(self, bucket: str, object_key: str) -> bytes:
        """下载对象内容到内存（用于图片处理等后台任务）。"""
        raise NotImplementedError

    async def put_object_bytes(
        self, bucket: str, object_key: str, data: bytes, content_type: str
    ) -> None:
        """上传字节到对象存储（用于写入派生图）。"""
        raise NotImplementedError