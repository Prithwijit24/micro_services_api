import httpx

from fastapi import APIRouter, HTTPException

from app.models import BrowseRequest, BrowseResponse

router = APIRouter()

BROWSE_TIMEOUT = 15  # seconds


@router.post("/browse", response_model=BrowseResponse)
async def browse(req: BrowseRequest):
    # NOTE: Playwright/Firefox browser layers are pending fix (Docker sandbox issue).
    # Currently using simple httpx fetch for content; screenshot/click/fill disabled.
    if req.action != "content":
        raise HTTPException(
            status_code=501,
            detail=f"Action '{req.action}' not available — browser layers pending fix. Use action='content'."
        )
    try:
        async with httpx.AsyncClient(timeout=BROWSE_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(str(req.url), headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return BrowseResponse(
                url=str(req.url), action=req.action, content=resp.text, success=True
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Browse failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Browse error: {e}")
