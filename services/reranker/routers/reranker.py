from fastapi import APIRouter, HTTPException

from models import RerankRequest, RerankResponse
from service import reranker_service

router = APIRouter()


@router.post("/rerank", response_model=RerankResponse)
async def rerank(req: RerankRequest):
    try:
        return await reranker_service.rerank(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rerank error: {e}")
