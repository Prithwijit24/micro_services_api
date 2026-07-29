from fastapi import APIRouter, HTTPException

from app.models import EmbedRequest, EmbedResponse
from app.services.embed import EmbedService

router = APIRouter()
svc = EmbedService()


@router.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    try:
        return await svc.embed(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
