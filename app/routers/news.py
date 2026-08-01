from fastapi import APIRouter, HTTPException

from app.models import NewsSearchRequest, NewsSearchResponse
from app.services.news import news_service

router = APIRouter(prefix="/news")


@router.post("", response_model=NewsSearchResponse)
async def search_news(req: NewsSearchRequest):
    """Search news via DDGS, optionally crawl full article content."""
    try:
        return await news_service.search(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
