from fastapi import APIRouter, HTTPException

from models import (
    YoutubeInfoRequest, YoutubeInfoResponse,
    YoutubeDownloadRequest, JobResponse,
    TranscriptRequest, TranscriptResponse,
    ThumbnailRequest,
)
from service import youtube_service

router = APIRouter(prefix="/youtube")


@router.post("/info", response_model=YoutubeInfoResponse)
async def info(req: YoutubeInfoRequest):
    try:
        return await youtube_service.info(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"yt-dlp error: {e}")


@router.post("/download/audio", response_model=JobResponse)
async def download_audio(req: YoutubeDownloadRequest):
    return await youtube_service.start_download(req, media_type="audio")


@router.post("/download/video", response_model=JobResponse)
async def download_video(req: YoutubeDownloadRequest):
    return await youtube_service.start_download(req, media_type="video")


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def job_status(job_id: str):
    job = youtube_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/transcript", response_model=TranscriptResponse)
async def transcript(req: TranscriptRequest):
    try:
        return await youtube_service.transcript(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"yt-dlp error: {e}")


@router.post("/thumbnail", response_model=YoutubeInfoResponse)
async def thumbnail(req: ThumbnailRequest):
    try:
        return await youtube_service.info(YoutubeInfoRequest(url=req.url))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"yt-dlp error: {e}")
