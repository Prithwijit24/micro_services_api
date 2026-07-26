from fastapi import APIRouter, HTTPException
import httpx

from models import CrawlRequest, CrawlResponse
from service import crawl_service

router = APIRouter()


@router.post("/crawl", response_model=CrawlResponse)
async def crawl(req: CrawlRequest):
    try:
        return await crawl_service.crawl(req)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Firecrawl upstream error: {e}")
