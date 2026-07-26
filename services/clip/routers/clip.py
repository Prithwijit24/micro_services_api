from fastapi import APIRouter, HTTPException

from models import (
    TextEmbeddingRequest, ImageEmbeddingRequest, EmbeddingResponse,
    SimilarityRequest, SimilarityResponse,
)
from service import clip_service

router = APIRouter(prefix="/clip")


@router.post("/text_embedding", response_model=EmbeddingResponse)
async def text_embedding(req: TextEmbeddingRequest):
    try:
        return await clip_service.text_embedding(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLIP text embedding error: {e}")


@router.post("/image_embedding", response_model=EmbeddingResponse)
async def image_embedding(req: ImageEmbeddingRequest):
    if not req.image_urls and not req.images_base64:
        raise HTTPException(status_code=400, detail="Provide image_urls or images_base64")
    try:
        return await clip_service.image_embedding(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLIP image embedding error: {e}")


@router.post("/similarity", response_model=SimilarityResponse)
async def similarity(req: SimilarityRequest):
    if not req.image_urls and not req.images_base64:
        raise HTTPException(status_code=400, detail="Provide image_urls or images_base64")
    try:
        return await clip_service.similarity(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLIP similarity error: {e}")
