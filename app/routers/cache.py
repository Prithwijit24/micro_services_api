from fastapi import APIRouter, HTTPException

from app.models import CacheSetRequest, CacheSetResponse, CacheGetResponse, CacheDeleteResponse
from app.services.cache import CacheService

router = APIRouter(prefix="/cache")
svc = CacheService()


@router.post("/set", response_model=CacheSetResponse)
async def set_key(req: CacheSetRequest):
    try:
        success = await svc.set(req.key, req.value, req.ttl_seconds)
        return CacheSetResponse(key=req.key, success=success)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get/{key}", response_model=CacheGetResponse)
async def get_key(key: str):
    try:
        value, found = await svc.get(key)
        return CacheGetResponse(key=key, value=value, found=found)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{key}", response_model=CacheDeleteResponse)
async def delete_key(key: str):
    try:
        deleted = await svc.delete(key)
        return CacheDeleteResponse(key=key, deleted=deleted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
