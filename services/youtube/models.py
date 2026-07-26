from typing import Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class YoutubeInfoRequest(BaseModel):
    url: HttpUrl


class YoutubeInfoResponse(BaseModel):
    id: str
    title: str
    duration: Optional[int] = None
    uploader: Optional[str] = None
    view_count: Optional[int] = None
    thumbnail: Optional[str] = None
    webpage_url: str


class YoutubeDownloadRequest(BaseModel):
    url: HttpUrl
    quality: Optional[str] = Field(default="best", description="e.g. best, worst, 720p")


class JobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    result_path: Optional[str] = None
    error: Optional[str] = None


class TranscriptRequest(BaseModel):
    url: HttpUrl
    language: str = Field(default="en")


class TranscriptResponse(BaseModel):
    id: str
    language: str
    segments: list[dict]


class ThumbnailRequest(BaseModel):
    url: HttpUrl
