from fastapi import APIRouter, HTTPException

from app.models import RerankRequest, RerankResponse
from app.services.reranker import RerankerService

router = APIRouter()
svc = RerankerService()


@router.post("/rerank", response_model=RerankResponse)
async def rerank(req: RerankRequest):
    try:
        return await svc.rerank(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
