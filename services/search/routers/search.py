from fastapi import APIRouter, HTTPException
import httpx

from models import SearchRequest, SearchResponse
from service import search_service

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        return await search_service.search(req)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"SearXNG upstream error: {e}")
