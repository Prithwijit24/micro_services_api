from fastapi import APIRouter, HTTPException

from models import BrowseRequest, BrowseResponse
from service import browser_service

router = APIRouter()


@router.post("/browse", response_model=BrowseResponse)
async def browse(req: BrowseRequest):
    try:
        return await browser_service.browse(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Browser automation error: {e}")
