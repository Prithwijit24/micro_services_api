from fastapi import APIRouter, HTTPException

from app.models import BrowseRequest, BrowseResponse
from app.services.browse import BrowserService

router = APIRouter()
svc = BrowserService()


@router.post("/browse", response_model=BrowseResponse)
async def browse(req: BrowseRequest):
    try:
        return await svc.browse(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
