from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response

from app.models import StorageUploadRequest, StorageUploadResponse
from app.models import StorageListRequest, StorageListResponse
from app.models import StorageDeleteRequest, StorageDeleteResponse
from app.services.storage import storage_service

router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("/upload", response_model=StorageUploadResponse)
async def upload(
    key: str = Form(...),
    bucket: str = Form(default=None),
    content_type: str = Form(default=None),
    file: UploadFile = File(...),
):
    try:
        file_bytes = await file.read()
        req = StorageUploadRequest(
            key=key,
            bucket=bucket,
            content_type=content_type or file.content_type,
        )
        return await storage_service.upload(req, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{bucket}/{key:path}")
async def download(bucket: str, key: str):
    try:
        data, content_type = await storage_service.download(bucket, key)
        return Response(content=data, media_type=content_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list", response_model=StorageListResponse)
async def list_files(req: StorageListRequest):
    try:
        return await storage_service.list_files(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=StorageDeleteResponse)
async def delete_files(req: StorageDeleteRequest):
    try:
        return await storage_service.delete(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
