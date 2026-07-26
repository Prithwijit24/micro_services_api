import os
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

from models import (
    YoutubeInfoRequest, YoutubeInfoResponse,
    YoutubeDownloadRequest, JobResponse,
    TranscriptRequest, TranscriptResponse,
)

logger = logging.getLogger("youtube")

DOWNLOAD_DIR = os.getenv("YOUTUBE_DOWNLOAD_DIR", "/opt/data/youtube")
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("YOUTUBE_MAX_CONCURRENT_DOWNLOADS", "2"))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS)
_jobs: dict[str, JobResponse] = {}


class YoutubeService:

    async def info(self, req: YoutubeInfoRequest) -> YoutubeInfoResponse:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(_executor, self._extract_info, str(req.url))
        return YoutubeInfoResponse(
            id=data.get("id"),
            title=data.get("title"),
            duration=data.get("duration"),
            uploader=data.get("uploader"),
            view_count=data.get("view_count"),
            thumbnail=data.get("thumbnail"),
            webpage_url=data.get("webpage_url", str(req.url)),
        )

    def _extract_info(self, url: str) -> dict:
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def start_download(self, req: YoutubeDownloadRequest, media_type: str) -> JobResponse:
        job_id = str(uuid.uuid4())
        job = JobResponse(job_id=job_id, status="queued")
        _jobs[job_id] = job

        loop = asyncio.get_event_loop()
        loop.run_in_executor(_executor, self._download_worker, job_id, str(req.url), req.quality, media_type)
        return job

    def _download_worker(self, job_id: str, url: str, quality: str, media_type: str):
        _jobs[job_id].status = "running"
        try:
            out_tmpl = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
            if media_type == "audio":
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": out_tmpl,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                    }],
                    "quiet": True,
                    "retries": 5,
                }
            else:
                fmt = "best" if quality in (None, "best") else f"{quality}+bestaudio/best"
                ydl_opts = {"format": fmt, "outtmpl": out_tmpl, "quiet": True, "retries": 5}

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = ydl.prepare_filename(info)

            _jobs[job_id].status = "done"
            _jobs[job_id].result_path = filepath
        except Exception as e:
            logger.exception("Download failed for job %s", job_id)
            _jobs[job_id].status = "failed"
            _jobs[job_id].error = str(e)

    def get_job(self, job_id: str) -> JobResponse | None:
        return _jobs.get(job_id)

    async def transcript(self, req: TranscriptRequest) -> TranscriptResponse:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(_executor, self._extract_transcript, str(req.url), req.language)
        return TranscriptResponse(id=data["id"], language=req.language, segments=data["segments"])

    def _extract_transcript(self, url: str, language: str) -> dict:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [language],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        subs = (info.get("subtitles") or {}).get(language) or (info.get("automatic_captions") or {}).get(language, [])
        return {"id": info.get("id"), "segments": subs}


youtube_service = YoutubeService()
