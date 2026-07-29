from fastapi import APIRouter, HTTPException

from app.models import (
    UpsertRequest,
    UpsertResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorDeleteRequest,
    VectorDeleteResponse,
)
from app.services.vector import VectorService

router = APIRouter(prefix="/vector")
svc = VectorService()


@router.post("/upsert", response_model=UpsertResponse)
async def upsert(req: UpsertRequest):
    try:
        return await svc.upsert(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=VectorSearchResponse)
async def search(req: VectorSearchRequest):
    try:
        return await svc.search(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=VectorDeleteResponse)
async def delete(req: VectorDeleteRequest):
    try:
        return await svc.delete(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
