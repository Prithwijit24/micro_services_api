from fastapi import APIRouter, HTTPException

from models import SetRequest, SetResponse, GetResponse, DeleteResponse
from service import cache_service

router = APIRouter(prefix="/cache")


@router.post("/set", response_model=SetResponse)
async def set_key(req: SetRequest):
    try:
        success = await cache_service.set(req.key, req.value, req.ttl_seconds)
        return SetResponse(key=req.key, success=success)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache set error: {e}")


@router.get("/get/{key}", response_model=GetResponse)
async def get_key(key: str):
    try:
        value, found = await cache_service.get(key)
        return GetResponse(key=key, value=value, found=found)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache get error: {e}")


@router.delete("/delete/{key}", response_model=DeleteResponse)
async def delete_key(key: str):
    try:
        deleted = await cache_service.delete(key)
        return DeleteResponse(key=key, deleted=deleted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache delete error: {e}")
