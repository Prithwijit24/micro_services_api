from fastapi import APIRouter, HTTPException

from app.models import SearchRequest, SearchResponse
from app.services.search import SearchService

router = APIRouter(prefix="/search")
svc = SearchService()


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        return await svc.search(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
