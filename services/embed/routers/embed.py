from fastapi import APIRouter, HTTPException

from models import EmbedRequest, EmbedResponse
from service import embed_service

router = APIRouter()


@router.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    try:
        return await embed_service.embed(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")
