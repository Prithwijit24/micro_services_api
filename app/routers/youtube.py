from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.models import (
    YoutubeInfoRequest,
    YoutubeInfoResponse,
    YoutubeDownloadRequest,
    JobResponse,
    TranscriptRequest,
    TranscriptResponse,
    ThumbnailRequest,
)
from app.services.youtube import YoutubeService

router = APIRouter(prefix="/youtube")
svc = YoutubeService()


def _transcript_to_markdown(result: TranscriptResponse) -> str:
    """Convert a TranscriptResponse to a formatted markdown string."""
    lines = []
    lines.append(f"# Transcript: {result.id}")
    lines.append("")
    lines.append(f"**Video ID:** {result.id}")
    lines.append(f"**Language:** {result.language}")
    lines.append(f"**Source:** {result.source or 'unknown'}")
    if result.whisper_model:
        lines.append(f"**Whisper Model:** {result.whisper_model}")
    lines.append(f"**Segments:** {len(result.segments)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Full Transcript")
    lines.append("")

    for seg in result.segments:
        start = seg.get("start", 0)
        text = seg.get("text", "").strip()
        ts = str(timedelta(seconds=int(start)))
        lines.append(f"**[{ts}]** {text}")
        lines.append("")

    lines.append("---")
    lines.append("")
    if result.whisper_model:
        lines.append(f"*Transcribed using Whisper {result.whisper_model} (faster-whisper)*")
    lines.append("")

    return "\n".join(lines)


@router.post("/info", response_model=YoutubeInfoResponse)
async def info(req: YoutubeInfoRequest):
    try:
        return await svc.info(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/download/audio", response_model=JobResponse)
async def download_audio(req: YoutubeDownloadRequest):
    return await svc.start_download(req, media_type="audio")


@router.post("/download/video", response_model=JobResponse)
async def download_video(req: YoutubeDownloadRequest):
    return await svc.start_download(req, media_type="video")


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def job_status(job_id: str):
    job = svc.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/transcript")
async def transcript(
    req: TranscriptRequest,
    output_format: Literal["json", "markdown"] = Query(
        default="json", description="Output format: 'json' or 'markdown'"
    ),
):
    try:
        result = await svc.transcript(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if output_format == "markdown":
        md = _transcript_to_markdown(result)
        return PlainTextResponse(content=md, media_type="text/markdown")

    return result


@router.post("/thumbnail", response_model=YoutubeInfoResponse)
async def thumbnail(req: ThumbnailRequest):
    try:
        return await svc.info(YoutubeInfoRequest(url=req.url))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
