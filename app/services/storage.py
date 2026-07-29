"""MinIO / S3-compatible file storage service."""

import os
import logging
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.models import (
    StorageUploadRequest,
    StorageUploadResponse,
    StorageDownloadResponse,
    StorageListRequest,
    StorageListResponse,
    StorageDeleteRequest,
    StorageDeleteResponse,
    StorageFileItem,
)

logger = logging.getLogger("storage")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "ai-stack")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


class StorageService:
    def __init__(self):
        self._client: Optional[Minio] = None

    def _get_client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )
        return self._client

    def _ensure_bucket(self, client: Minio, bucket: str):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

    async def upload(self, req: StorageUploadRequest, file_bytes: bytes) -> StorageUploadResponse:
        client = self._get_client()
        bucket = req.bucket or MINIO_BUCKET
        self._ensure_bucket(client, bucket)

        from io import BytesIO
        content_type = req.content_type or "application/octet-stream"

        client.put_object(
            bucket,
            req.key,
            BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )

        return StorageUploadResponse(
            bucket=bucket,
            key=req.key,
            size=len(file_bytes),
            url=f"s3://{bucket}/{req.key}",
        )

    async def download(self, bucket: str, key: str) -> tuple[bytes, str]:
        client = self._get_client()
        bucket = bucket or MINIO_BUCKET

        try:
            obj = client.get_object(bucket, key)
            data = obj.read()
            content_type = obj.headers.get("Content-Type", "application/octet-stream")
            obj.close()
            obj.release_conn()
            return data, content_type
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {bucket}/{key}")
            raise

    async def list_files(self, req: StorageListRequest) -> StorageListResponse:
        client = self._get_client()
        bucket = req.bucket or MINIO_BUCKET

        try:
            objects = client.list_objects(
                bucket,
                prefix=req.prefix or "",
                recursive=True,
            )

            files = []
            for obj in objects:
                files.append(StorageFileItem(
                    key=obj.object_name,
                    size=obj.size,
                    last_modified=obj.last_modified.isoformat() if obj.last_modified else None,
                    etag=obj.etag,
                ))

            return StorageListResponse(
                bucket=bucket,
                prefix=req.prefix or "",
                files=files,
                count=len(files),
            )
        except S3Error as e:
            if e.code == "NoSuchBucket":
                return StorageListResponse(bucket=bucket, prefix=req.prefix or "", files=[], count=0)
            raise

    async def delete(self, req: StorageDeleteRequest) -> StorageDeleteResponse:
        client = self._get_client()
        bucket = req.bucket or MINIO_BUCKET

        deleted = 0
        errors = []

        for key in req.keys:
            try:
                client.remove_object(bucket, key)
                deleted += 1
            except S3Error as e:
                errors.append(f"{key}: {e}")

        return StorageDeleteResponse(
            bucket=bucket,
            deleted=deleted,
            errors=errors if errors else None,
        )

    async def delete_bucket(self, bucket: str) -> bool:
        client = self._get_client()
        try:
            client.remove_bucket(bucket)
            return True
        except S3Error:
            return False


storage_service = StorageService()
