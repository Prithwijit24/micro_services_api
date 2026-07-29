from fastapi import APIRouter, HTTPException

from app.models import (
    TextEmbeddingRequest,
    ImageEmbeddingRequest,
    ClipEmbeddingResponse,
    SimilarityRequest,
    SimilarityResponse,
)
from app.services.clip import ClipService

router = APIRouter(prefix="/clip")
svc = ClipService()


@router.post("/text_embedding", response_model=ClipEmbeddingResponse)
async def text_embedding(req: TextEmbeddingRequest):
    try:
        return await svc.text_embedding(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image_embedding", response_model=ClipEmbeddingResponse)
async def image_embedding(req: ImageEmbeddingRequest):
    if not req.image_urls and not req.images_base64:
        raise HTTPException(status_code=400, detail="Provide image_urls or images_base64")
    try:
        return await svc.image_embedding(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similarity", response_model=SimilarityResponse)
async def similarity(req: SimilarityRequest):
    if not req.image_urls and not req.images_base64:
        raise HTTPException(status_code=400, detail="Provide image_urls or images_base64")
    try:
        return await svc.similarity(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
