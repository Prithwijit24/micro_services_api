from fastapi import APIRouter, HTTPException

from models import (
    UpsertRequest, UpsertResponse,
    SearchRequest, SearchResponse,
    DeleteRequest, DeleteResponse,
)
from service import vector_service

router = APIRouter(prefix="/vector")


@router.post("/upsert", response_model=UpsertResponse)
async def upsert(req: UpsertRequest):
    try:
        return await vector_service.upsert(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector upsert error: {e}")


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        return await vector_service.search(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search error: {e}")


@router.post("/delete", response_model=DeleteResponse)
async def delete(req: DeleteRequest):
    try:
        return await vector_service.delete(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector delete error: {e}")
