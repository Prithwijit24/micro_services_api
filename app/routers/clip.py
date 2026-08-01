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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image_embedding", response_model=ClipEmbeddingResponse)
async def image_embedding(req: ImageEmbeddingRequest):
    try:
        return await svc.image_embedding(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similarity", response_model=SimilarityResponse)
async def similarity(req: SimilarityRequest):
    try:
        return await svc.similarity(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
