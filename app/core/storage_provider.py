"""
Storage Provider Abstraction Layer

Cung cấp interface thống nhất để lưu trữ graph data (GraphML/JSON).
Hỗ trợ switching giữa Local Storage (dev/staging) và S3 (production cloud)
mà không cần thay đổi business logic.

Usage:
    from app.core.storage_provider import get_storage_provider
    
    storage = get_storage_provider()
    await storage.save("graph_123.graphml", graphml_data)
    data = await storage.load("graph_123.graphml")
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from datetime import datetime

import aiofiles
from loguru import logger

from app.config import settings


class StorageProvider(ABC):
    """Abstract base class cho storage backend."""
    
    @abstractmethod
    async def save(self, key: str, data: bytes) -> str:
        """
        Lưu data với key nhất định.
        
        Args:
            key: Identifier cho data (e.g., "graph_{document_id}.graphml")
            data: Bytes data cần lưu
            
        Returns:
            Path hoặc URL đến data đã lưu
        """
        pass
    
    @abstractmethod
    async def load(self, key: str) -> Optional[bytes]:
        """
        Load data từ key.
        
        Args:
            key: Identifier cho data
            
        Returns:
            Bytes data hoặc None nếu không tồn tại
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Kiểm tra xem key có tồn tại không."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Xóa data với key.
        
        Returns:
            True nếu xóa thành công, False nếu không tồn tại
        """
        pass
    
    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        Liệt kê tất cả keys với prefix nhất định.
        
        Args:
            prefix: Filter keys bằng prefix này
            
        Returns:
            Danh sách keys
        """
        pass


class LocalStorage(StorageProvider):
    """
    Local filesystem storage implementation.
    Phù hợp cho development, staging, hoặc single-server deployment.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.GRAPH_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorage initialized: {self.base_path}")
    
    def _get_full_path(self, key: str) -> Path:
        """Tính full path từ key, ngăn chặn path traversal."""
        # Sanitize key để ngăn chặn path traversal
        safe_key = key.replace("..", "").replace("/", os.sep)
        full_path = self.base_path / safe_key
        
        # Verify rằng path nằm trong base_path
        try:
            full_path.resolve().relative_to(self.base_path.resolve())
        except ValueError:
            raise ValueError(f"Invalid key (path traversal detected): {key}")
        
        return full_path
    
    async def save(self, key: str, data: bytes) -> str:
        """Lưu data ra local file."""
        full_path = self._get_full_path(key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)
        
        logger.debug(f"LocalStorage saved: {key} -> {full_path}")
        return str(full_path)
    
    async def load(self, key: str) -> Optional[bytes]:
        """Load data từ local file."""
        full_path = self._get_full_path(key)
        
        if not full_path.exists():
            logger.debug(f"LocalStorage key not found: {key}")
            return None
        
        async with aiofiles.open(full_path, "rb") as f:
            data = await f.read()
        
        logger.debug(f"LocalStorage loaded: {key} ({len(data)} bytes)")
        return data
    
    async def exists(self, key: str) -> bool:
        """Kiểm tra file tồn tại."""
        full_path = self._get_full_path(key)
        return full_path.exists()
    
    async def delete(self, key: str) -> bool:
        """Xóa file."""
        full_path = self._get_full_path(key)
        
        if not full_path.exists():
            return False
        
        full_path.unlink()
        logger.debug(f"LocalStorage deleted: {key}")
        return True
    
    async def list_keys(self, prefix: str = "") -> list[str]:
        """Liệt kê files với prefix."""
        search_path = self.base_path / prefix if prefix else self.base_path
        
        if not search_path.exists():
            return []
        
        keys = []
        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(self.base_path)
                keys.append(str(relative))
        
        return sorted(keys)


class S3Storage(StorageProvider):
    """
    S3-compatible storage implementation.
    Phù hợp cho production cloud deployment (AWS S3, MinIO, DigitalOcean Spaces).
    
    Yêu cầu: boto3 và credentials cấu hình qua env vars.
    """
    
    def __init__(
        self,
        bucket: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
    ):
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
        except ImportError:
            raise ImportError(
                "boto3 is required for S3Storage. Install with: pip install boto3"
            )
        
        self.bucket = bucket or os.getenv("S3_BUCKET", "aethertutor-graphs")
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.region = region or os.getenv("S3_REGION", "us-east-1")
        
        # Khởi tạo S3 client
        session_kwargs = {}
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        
        session = boto3.Session(**session_kwargs)
        
        client_kwargs = {"region_name": self.region}
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        
        self.s3_client = session.client("s3", **client_kwargs)
        self.ClientError = ClientError
        
        logger.info(
            f"S3Storage initialized: bucket={self.bucket}, "
            f"endpoint={self.endpoint_url or 'AWS S3'}"
        )
    
    def _get_key(self, key: str) -> str:
        """Sanitize S3 key."""
        return key.replace("\\", "/").lstrip("/")
    
    async def save(self, key: str, data: bytes) -> str:
        """Upload data lên S3."""
        s3_key = self._get_key(key)
        
        # S3 upload là sync operation, chạy trong thread executor
        import asyncio
        loop = asyncio.get_event_loop()
        
        await loop.run_in_executor(
            None,
            lambda: self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=data,
            )
        )
        
        url = f"s3://{self.bucket}/{s3_key}"
        logger.debug(f"S3Storage saved: {key} -> {url}")
        return url
    
    async def load(self, key: str) -> Optional[bytes]:
        """Load data từ S3."""
        s3_key = self._get_key(key)
        
        import asyncio
        loop = asyncio.get_event_loop()
        
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.get_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                )
            )
            data = response["Body"].read()
            logger.debug(f"S3Storage loaded: {key} ({len(data)} bytes)")
            return data
        except self.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.debug(f"S3Storage key not found: {key}")
                return None
            raise
    
    async def exists(self, key: str) -> bool:
        """Kiểm tra object tồn tại trong S3."""
        s3_key = self._get_key(key)
        
        import asyncio
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                )
            )
            return True
        except self.ClientError:
            return False
    
    async def delete(self, key: str) -> bool:
        """Xóa object từ S3."""
        s3_key = self._get_key(key)
        
        import asyncio
        loop = asyncio.get_event_loop()
        
        if not await self.exists(key):
            return False
        
        await loop.run_in_executor(
            None,
            lambda: self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=s3_key,
            )
        )
        
        logger.debug(f"S3Storage deleted: {key}")
        return True
    
    async def list_keys(self, prefix: str = "") -> list[str]:
        """Liệt kê objects trong S3 bucket."""
        import asyncio
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None,
            lambda: self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=self._get_key(prefix),
            )
        )
        
        keys = []
        for obj in response.get("Contents", []):
            keys.append(obj["Key"])
        
        return sorted(keys)


# Singleton instance cho storage provider
_storage_provider: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    """
    Factory function để lấy storage provider instance.
    Đọc config từ settings để quyết định dùng Local hay S3.
    """
    global _storage_provider
    
    if _storage_provider is not None:
        return _storage_provider
    
    backend = getattr(settings, "GRAPH_STORAGE_BACKEND", "local")
    
    if backend == "local":
        _storage_provider = LocalStorage()
    elif backend == "s3":
        _storage_provider = S3Storage()
    else:
        raise ValueError(f"Unknown storage backend: {backend}. Use 'local' or 's3'.")
    
    return _storage_provider


def reset_storage_provider():
    """Reset singleton (chỉ dùng cho testing)."""
    global _storage_provider
    _storage_provider = None
