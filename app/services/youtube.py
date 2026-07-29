"""YouTube download/info/transcript service via yt-dlp + Whisper fallback."""

import os
import uuid
import asyncio
import logging
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

from app.models import (
    YoutubeInfoRequest,
    YoutubeInfoResponse,
    YoutubeDownloadRequest,
    JobResponse,
    TranscriptRequest,
    TranscriptResponse,
)

logger = logging.getLogger("youtube")

DOWNLOAD_DIR = os.getenv("YOUTUBE_DOWNLOAD_DIR", "/opt/data/youtube")
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("YOUTUBE_MAX_CONCURRENT_DOWNLOADS", "2"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large-v3
WHISPER_MAX_DURATION = int(os.getenv("WHISPER_MAX_DURATION", "3600"))  # seconds (0 = no limit)

_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS)
_jobs: dict[str, JobResponse] = {}

# Lazy-loaded Whisper model (loaded once on first use, thread-safe)
_whisper_model = None
_whisper_lock = threading.Lock()


def _get_whisper_model():
    """Load the Whisper model once and cache it (thread-safe)."""
    global _whisper_model
    if _whisper_model is None:
        with _whisper_lock:
            # Double-check after acquiring lock
            if _whisper_model is None:
                from faster_whisper import WhisperModel

                logger.info("Loading Whisper model '%s' (first use)...", WHISPER_MODEL)
                device = "auto"  # faster-whisper auto-detects GPU
                _whisper_model = WhisperModel(WHISPER_MODEL, device=device, compute_type="int8")
                logger.info("Whisper model '%s' loaded.", WHISPER_MODEL)
    return _whisper_model


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
        import yt_dlp

        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def start_download(self, req: YoutubeDownloadRequest, media_type: str) -> JobResponse:
        job_id = str(uuid.uuid4())
        job = JobResponse(job_id=job_id, status="queued")
        _jobs[job_id] = job

        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _executor, self._download_worker, job_id, str(req.url), req.quality, media_type
        )
        return job

    def _download_worker(self, job_id: str, url: str, quality: str, media_type: str):
        import yt_dlp

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        _jobs[job_id].status = "running"
        try:
            out_tmpl = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
            if media_type == "audio":
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": out_tmpl,
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
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
        data = await loop.run_in_executor(
            _executor, self._extract_transcript, str(req.url), req.language, req.force_whisper
        )
        return TranscriptResponse(
            id=data["id"], language=req.language, segments=data["segments"],
            source=data.get("source"), whisper_model=data.get("whisper_model"),
        )

    def _extract_transcript(self, url: str, language: str, force_whisper: bool = False) -> dict:
        """Extract transcript: try YouTube subtitles first, fall back to Whisper STT."""
        import yt_dlp

        # ── Fetch video info once (reused for subtitles + duration check) ─
        info = None
        vid_id = "unknown"
        if not force_whisper:
            try:
                ydl_opts = {
                    "quiet": True,
                    "skip_download": True,
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": [language],
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                vid_id = info.get("id", "unknown")
            except Exception as e:
                logger.warning("YouTube info extraction failed: %s", e)

        # ── Step 1: Try YouTube subtitles/captions ────────────────────────
        if info and not force_whisper:
            subs = (info.get("subtitles") or {}).get(language) or (
                info.get("automatic_captions") or {}
            ).get(language, [])
            if subs and any(s.get("text", "").strip() for s in subs):
                logger.info("Using YouTube subtitles for %s (%d segments)", vid_id, len(subs))
                return {"id": vid_id, "segments": subs, "source": "youtube_subtitles"}
            logger.info("No usable YouTube subtitles for %s, trying Whisper...", vid_id)

        # ── Step 2: Check duration before Whisper transcription ───────────
        if WHISPER_MAX_DURATION > 0:
            try:
                if info is None:
                    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                    vid_id = info.get("id", "unknown")
                duration = info.get("duration", 0) or 0
                if duration > WHISPER_MAX_DURATION:
                    raise RuntimeError(
                        f"Video {vid_id} is {duration}s long ({duration // 60}min), "
                        f"exceeds WHISPER_MAX_DURATION={WHISPER_MAX_DURATION}s limit. "
                        f"Use YouTube subtitles or set WHISPER_MAX_DURATION=0 to disable."
                    )
                logger.info("Video %s duration: %ds (limit: %ds)", vid_id, duration, WHISPER_MAX_DURATION)
            except Exception as e:
                if isinstance(e, RuntimeError):
                    raise
                logger.warning("Duration check failed for %s: %s", url, e)

        # ── Step 3: Download audio and transcribe with Whisper ────────────
        return self._whisper_transcribe(url, language)

    def _whisper_transcribe(self, url: str, language: str) -> dict:
        """Download audio from YouTube and transcribe with Whisper."""
        import yt_dlp
        import glob as _glob

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use placeholder name — yt-dlp postprocessor renames the file
            out_tmpl = os.path.join(tmpdir, "audio")

            # Download audio only (best quality, extract to mp3)
            logger.info("Downloading audio from %s for Whisper transcription...", url)
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_tmpl,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
                "quiet": True,
                "retries": 3,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                vid_id = info.get("id", "unknown")

            # Find the actual audio file (postprocessor may rename it)
            audio_files = _glob.glob(os.path.join(tmpdir, "audio.*"))
            if not audio_files:
                raise RuntimeError(f"Audio download failed for {url}")
            audio_path = audio_files[0]
            logger.info("Audio downloaded to %s (%.1f MB)", audio_path, os.path.getsize(audio_path) / 1e6)

            # Transcribe with Whisper
            logger.info("Transcribing %s with Whisper model '%s'...", vid_id, WHISPER_MODEL)
            model = _get_whisper_model()
            segments_gen, info = model.transcribe(
                audio_path,
                beam_size=5,
                language=language if language != "auto" else None,
            )

            segments = []
            for seg in segments_gen:
                segments.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                })

            logger.info(
                "Whisper transcription complete: %d segments, detected language=%s (%.2f%%)",
                len(segments),
                info.language,
                info.language_probability * 100,
            )
            return {
                "id": vid_id,
                "segments": segments,
                "source": "whisper",
                "whisper_model": WHISPER_MODEL,
            }


youtube_service = YoutubeService()
