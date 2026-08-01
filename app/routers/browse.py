from fastapi import APIRouter, HTTPException

from app.models import BrowseRequest, BrowseResponse
from app.services.browse import BrowserService
from app.services.url_policy import UnsafeURL

router = APIRouter()
svc = BrowserService()


@router.post("/browse", response_model=BrowseResponse)
async def browse(req: BrowseRequest):
    try:
        return await svc.browse(req)
    except UnsafeURL as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=502, detail="Browse failed")
