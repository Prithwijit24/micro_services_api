"""MinIO / S3-compatible file storage service."""

from __future__ import annotations

import asyncio
import logging
import os
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.models import (
    StorageDeleteRequest,
    StorageDeleteResponse,
    StorageFileItem,
    StorageListRequest,
    StorageListResponse,
    StorageUploadRequest,
    StorageUploadResponse,
)

logger = logging.getLogger("storage")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "ai-stack")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


def _name(value: str, field: str) -> str:
    if not value or len(value) > 1024 or "\x00" in value:
        raise ValueError(f"invalid {field}")
    return value


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

    def _ensure_bucket(self, client: Minio, bucket: str) -> None:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

    def _upload_sync(self, req: StorageUploadRequest, file_bytes: bytes) -> StorageUploadResponse:
        client = self._get_client()
        bucket = _name(req.bucket or MINIO_BUCKET, "bucket")
        key = _name(req.key, "key")
        self._ensure_bucket(client, bucket)
        client.put_object(
            bucket,
            key,
            BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=req.content_type or "application/octet-stream",
        )
        return StorageUploadResponse(
            bucket=bucket, key=key, size=len(file_bytes), url=f"s3://{bucket}/{key}"
        )

    async def upload(self, req: StorageUploadRequest, file_bytes: bytes) -> StorageUploadResponse:
        return await asyncio.to_thread(self._upload_sync, req, file_bytes)

    def _download_sync(self, bucket: str, key: str) -> tuple[bytes, str]:
        client = self._get_client()
        bucket = _name(bucket or MINIO_BUCKET, "bucket")
        key = _name(key, "key")
        obj = None
        try:
            obj = client.get_object(bucket, key)
            return obj.read(), obj.headers.get("Content-Type", "application/octet-stream")
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                raise FileNotFoundError(f"File not found: {bucket}/{key}") from exc
            raise
        finally:
            if obj is not None:
                obj.close()
                obj.release_conn()

    async def download(self, bucket: str, key: str) -> tuple[bytes, str]:
        return await asyncio.to_thread(self._download_sync, bucket, key)

    def _list_sync(self, req: StorageListRequest) -> StorageListResponse:
        client = self._get_client()
        bucket = _name(req.bucket or MINIO_BUCKET, "bucket")
        prefix = req.prefix or ""
        objects = client.list_objects(bucket, prefix=prefix, recursive=True)
        files = [
            StorageFileItem(
                key=obj.object_name,
                size=obj.size,
                last_modified=obj.last_modified.isoformat() if obj.last_modified else None,
                etag=obj.etag,
            )
            for obj in objects
        ]
        return StorageListResponse(bucket=bucket, prefix=prefix, files=files, count=len(files))

    async def list_files(self, req: StorageListRequest) -> StorageListResponse:
        try:
            return await asyncio.to_thread(self._list_sync, req)
        except S3Error as exc:
            if exc.code == "NoSuchBucket":
                bucket = req.bucket or MINIO_BUCKET
                return StorageListResponse(bucket=bucket, prefix=req.prefix or "", files=[], count=0)
            raise

    def _delete_sync(self, req: StorageDeleteRequest) -> StorageDeleteResponse:
        client = self._get_client()
        bucket = _name(req.bucket or MINIO_BUCKET, "bucket")
        deleted = 0
        errors: list[str] = []
        for raw_key in req.keys:
            key = _name(raw_key, "key")
            try:
                client.remove_object(bucket, key)
                deleted += 1
            except S3Error as exc:
                logger.warning("Storage delete failed for %s/%s: %s", bucket, key, exc.code)
                errors.append(key)
        return StorageDeleteResponse(bucket=bucket, deleted=deleted, errors=errors or None)

    async def delete(self, req: StorageDeleteRequest) -> StorageDeleteResponse:
        return await asyncio.to_thread(self._delete_sync, req)

    def close(self) -> None:
        self._client = None


storage_service = StorageService()
