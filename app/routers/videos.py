from fastapi import APIRouter, HTTPException

from app.models import VideoSearchRequest, VideoSearchResponse
from app.services.videos import video_service

router = APIRouter(prefix="/videos")


@router.post("", response_model=VideoSearchResponse)
async def search_videos(req: VideoSearchRequest):
    """Search videos via DDGS."""
    try:
        return await video_service.search(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
