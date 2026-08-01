from fastapi import APIRouter, HTTPException

from app.models import ImageSearchRequest, ImageSearchResponse
from app.services.images import image_service

router = APIRouter(prefix="/images")


@router.post("", response_model=ImageSearchResponse)
async def search_images(req: ImageSearchRequest):
    """Search images via DDGS → Unsplash → Pexels fallback chain, with CLIP reranking."""
    try:
        return await image_service.search(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
