"""Object storage service abstraction and adapters (S3 & Local).

Allows client pre-signed URL generation, upload authorization, and object retrieval
without coupling business logic directly to boto3.
"""

from abc import ABC, abstractmethod
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from sightsense_api.core.errors import UpstreamServiceError
from sightsense_api.core.logging import get_logger

logger = get_logger("sightsense_api.storage")


class StorageInterface(ABC):
    """Abstract object storage interface."""

    @abstractmethod
    async def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: str,
        content_length: int,
        expires_in_seconds: int = 900,
    ) -> str: ...

    @abstractmethod
    async def generate_presigned_download_url(
        self, object_key: str, expires_in_seconds: int = 900
    ) -> str: ...

    @abstractmethod
    async def get_object_bytes(self, object_key: str) -> bytes: ...

    @abstractmethod
    async def put_object_bytes(
        self, object_key: str, data: bytes, content_type: str = "image/jpeg"
    ) -> None: ...

    @abstractmethod
    async def delete_object(self, object_key: str) -> bool: ...


class LocalStorageAdapter(StorageInterface):
    """Local disk storage adapter for development and testing without AWS credentials."""

    def __init__(self, base_dir: Path | str = "./.local_storage") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: str,
        content_length: int,
        expires_in_seconds: int = 900,
    ) -> str:
        # Returns a mock local endpoint for direct simulation
        return f"http://localhost:8000/api/v1/uploads/mock-direct/{object_key}"

    async def generate_presigned_download_url(
        self, object_key: str, expires_in_seconds: int = 900
    ) -> str:
        return f"http://localhost:8000/api/v1/uploads/mock-direct/{object_key}"

    async def get_object_bytes(self, object_key: str) -> bytes:
        target = self.base_dir / object_key
        if not target.exists():
            return b""
        return target.read_bytes()

    async def put_object_bytes(
        self, object_key: str, data: bytes, content_type: str = "image/jpeg"
    ) -> None:
        target = self.base_dir / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    async def delete_object(self, object_key: str) -> bool:
        target = self.base_dir / object_key
        if target.exists():
            target.unlink()
            return True
        return False


class S3StorageAdapter(StorageInterface):
    """Production S3 adapter using Boto3."""

    def __init__(self, bucket_name: str, region_name: str = "ap-south-1") -> None:
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            "s3",
            region_name=region_name,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )

    async def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: str,
        content_length: int,
        expires_in_seconds: int = 900,
    ) -> str:
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key,
                    "ContentType": content_type,
                    "ContentLength": content_length,
                },
                ExpiresIn=expires_in_seconds,
            )
            return str(url)
        except ClientError as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            raise UpstreamServiceError(message="Could not generate upload URL")

    async def generate_presigned_download_url(
        self, object_key: str, expires_in_seconds: int = 900
    ) -> str:
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expires_in_seconds,
            )
            return str(url)
        except ClientError as e:
            logger.error(f"Failed to generate presigned download URL: {e}")
            raise UpstreamServiceError(message="Could not generate download URL")

    async def get_object_bytes(self, object_key: str) -> bytes:
        try:
            res = self.s3_client.get_object(Bucket=self.bucket_name, Key=object_key)
            return bytes(res["Body"].read())
        except ClientError as e:
            logger.error(f"Failed to fetch object {object_key}: {e}")
            raise UpstreamServiceError(message="Failed to read object from storage")

    async def put_object_bytes(
        self, object_key: str, data: bytes, content_type: str = "image/jpeg"
    ) -> None:
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except ClientError as e:
            logger.error(f"Failed to write object {object_key}: {e}")
            raise UpstreamServiceError(message="Failed to write object to storage")

    async def delete_object(self, object_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete object {object_key}: {e}")
            return False
