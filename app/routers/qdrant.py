from fastapi import APIRouter, HTTPException

from app.models import QdrantCreateCollectionRequest, QdrantCreateCollectionResponse
from app.models import QdrantCollectionsResponse
from app.models import QdrantUpsertRequest, QdrantUpsertResponse
from app.models import QdrantSearchRequest, QdrantSearchResponse
from app.models import QdrantDeleteRequest, QdrantDeleteResponse
from app.services.qdrant import qdrant_service

router = APIRouter(prefix="/qdrant", tags=["qdrant"])


@router.post("/collections", response_model=QdrantCreateCollectionResponse)
async def create_collection(req: QdrantCreateCollectionRequest):
    try:
        return await qdrant_service.create_collection(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections", response_model=QdrantCollectionsResponse)
async def list_collections():
    try:
        return await qdrant_service.list_collections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upsert", response_model=QdrantUpsertResponse)
async def upsert(req: QdrantUpsertRequest):
    try:
        return await qdrant_service.upsert(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=QdrantSearchResponse)
async def search(req: QdrantSearchRequest):
    try:
        return await qdrant_service.search(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=QdrantDeleteResponse)
async def delete(req: QdrantDeleteRequest):
    try:
        return await qdrant_service.delete(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
