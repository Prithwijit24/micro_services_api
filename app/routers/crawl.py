from fastapi import APIRouter, HTTPException

from app.models import CrawlRequest, CrawlResponse
from app.services.crawl import crawl_service

router = APIRouter()


@router.post("/crawl", response_model=CrawlResponse)
async def crawl(req: CrawlRequest):
    try:
        return await crawl_service.crawl(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
