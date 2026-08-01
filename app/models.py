"""All request/response models, grouped by service."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator


# ── Common responses ─────────────────────────────────────────────────────────


class RootResponse(BaseModel):
    service: str
    version: str
    docs: str
    health: str
    liveness: str


class LivenessResponse(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    services: dict[str, dict[str, str]]


# ── Search ──────────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    categories: Optional[str] = "general"
    language: Optional[str] = "en"
    max_results: int = Field(default=10, ge=1, le=50)
    safesearch: int = Field(default=1, ge=0, le=2)


class SearchResultItem(BaseModel):
    title: str
    url: str
    content: Optional[str] = None
    engine: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    number_of_results: int
    results: list[SearchResultItem]


# ── Browse ──────────────────────────────────────────────────────────────────


class BrowseRequest(BaseModel):
    url: HttpUrl
    action: Literal["screenshot", "content", "click", "fill_form"] = "content"
    selector: Optional[str] = Field(default=None, description="CSS selector for click/fill actions")
    text: Optional[str] = Field(default=None, description="Text to fill for fill_form action")
    full_page: bool = Field(default=True, description="Full page screenshot")
    wait_ms: int = Field(default=1000, ge=0, le=30000)


class BrowseResponse(BaseModel):
    url: str
    action: str
    content: Optional[str] = None
    screenshot_base64: Optional[str] = None
    success: bool = True
    message: Optional[str] = None


# ── Embed ───────────────────────────────────────────────────────────────────


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=128)
    normalize: bool = True


class EmbedResponse(BaseModel):
    model: str
    dimensions: int
    embeddings: list[list[float]]


# ── YouTube ─────────────────────────────────────────────────────────────────


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
    force_whisper: bool = Field(default=False, description="Skip subtitle check, always use Whisper STT")


class TranscriptResponse(BaseModel):
    id: str
    language: str
    segments: list[dict]
    source: Optional[str] = Field(default=None, description="'youtube_subtitles' or 'whisper'")
    whisper_model: Optional[str] = Field(default=None, description="Whisper model used if source is whisper")


class ThumbnailRequest(BaseModel):
    url: HttpUrl


# ── CLIP ────────────────────────────────────────────────────────────────────


class TextEmbeddingRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)


class ImageEmbeddingRequest(BaseModel):
    image_urls: Optional[list[str]] = Field(default=None, min_length=1, max_length=50)
    images_base64: Optional[list[str]] = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def require_image_source(self):
        if not self.image_urls and not self.images_base64:
            raise ValueError("provide image_urls or images_base64")
        return self


class ClipEmbeddingResponse(BaseModel):
    model: str
    dimensions: int
    embeddings: list[list[float]]


class SimilarityRequest(BaseModel):
    text: str = Field(..., min_length=1)
    image_urls: Optional[list[str]] = Field(default=None, min_length=1, max_length=50)
    images_base64: Optional[list[str]] = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def require_image_source(self):
        if not self.image_urls and not self.images_base64:
            raise ValueError("provide image_urls or images_base64")
        return self


class SimilarityResponse(BaseModel):
    text: str
    scores: list[float]


# ── Reranker ────────────────────────────────────────────────────────────────


class RerankRequest(BaseModel):
    query: str
    documents: list[str] = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1)


class RerankedDocument(BaseModel):
    index: int
    document: str
    score: float


class RerankResponse(BaseModel):
    model: str
    query: str
    results: list[RerankedDocument]


# ── Graph (Neo4j) ──────────────────────────────────────────────────────────


class GraphQueryRequest(BaseModel):
    cypher: str = Field(..., description="Parameterized Cypher query")
    parameters: dict[str, Any] = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    records: list[dict[str, Any]]
    count: int


class AddNodeRequest(BaseModel):
    label: str = Field(..., description="Node label, e.g. 'Person'")
    properties: dict[str, Any] = Field(default_factory=dict)
    merge_key: Optional[str] = Field(
        default=None, description="Property key to MERGE on instead of always CREATE"
    )


class AddNodeResponse(BaseModel):
    node_id: str
    label: str
    properties: dict[str, Any]


class AddEdgeRequest(BaseModel):
    from_label: str = Field(..., min_length=1)
    from_key: str = Field(..., min_length=1)
    from_value: Any
    to_label: str = Field(..., min_length=1)
    to_key: str = Field(..., min_length=1)
    to_value: Any
    relationship: str = Field(..., min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)


class AddEdgeResponse(BaseModel):
    relationship: str
    from_node: dict[str, Any]
    to_node: dict[str, Any]


# ── Vector (ChromaDB) ──────────────────────────────────────────────────────


class VectorRecord(BaseModel):
    id: str = Field(..., min_length=1)
    embedding: list[float]
    document: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertRequest(BaseModel):
    collection: str = Field(..., min_length=1)
    records: list[VectorRecord] = Field(..., min_length=1)


class UpsertResponse(BaseModel):
    collection: str
    upserted: int


class VectorSearchRequest(BaseModel):
    collection: str = Field(..., min_length=1)
    query_embedding: list[float]
    top_k: int = Field(default=5, ge=1, le=100)
    where: Optional[dict[str, Any]] = None


class SearchMatch(BaseModel):
    id: str
    score: float
    document: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorSearchResponse(BaseModel):
    collection: str
    matches: list[SearchMatch]


class VectorDeleteRequest(BaseModel):
    collection: str = Field(..., min_length=1)
    ids: list[str] = Field(..., min_length=1)


class VectorDeleteResponse(BaseModel):
    collection: str
    deleted: int


# ── Cache (Redis) ──────────────────────────────────────────────────────────


class CacheSetRequest(BaseModel):
    key: str = Field(..., min_length=1)
    value: Any
    ttl_seconds: Optional[int] = Field(default=None, ge=1)


class CacheSetResponse(BaseModel):
    key: str
    success: bool


class CacheGetResponse(BaseModel):
    key: str
    value: Optional[Any] = None
    found: bool


class CacheDeleteResponse(BaseModel):
    key: str
    deleted: bool


# ── Crawl (Scrapling + Trafilatura) ───────────────────────────────────────


class CrawlRequest(BaseModel):
    url: HttpUrl
    only_main_content: bool = Field(default=True)
    include_html: bool = Field(default=False)
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)


class CrawlResponse(BaseModel):
    url: str
    markdown: str
    html: Optional[str] = None
    title: Optional[str] = None
    status_code: Optional[int] = None


# ── DuckDB ─────────────────────────────────────────────────────────────────


class DuckDBQueryRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    params: Optional[list[Any]] = Field(default=None)


class DuckDBQueryResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    error: Optional[str] = None


class DuckDBInsertRequest(BaseModel):
    table: str = Field(..., min_length=1)
    columns: list[str] = Field(..., min_length=1)
    rows: list[dict[str, Any]] = Field(..., min_length=1)


class DuckDBInsertResponse(BaseModel):
    table: str
    inserted: int
    error: Optional[str] = None


class DuckDBTableResponse(BaseModel):
    tables: list[dict[str, Any]]
    error: Optional[str] = None


# ── Pipeline (Search → Crawl → Rerank) ─────────────────────────────────────


class PipelineRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The question to search and answer")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of final results to return")
    crawl_limit: int = Field(default=10, ge=1, le=30, description="Max URLs to crawl from search results")
    max_search_results: int = Field(default=15, ge=1, le=50, description="Max search results to fetch")
    max_markdown_chars: int = Field(default=5000, ge=500, le=50000, description="Max markdown chars per result")
    categories: Optional[str] = "general"
    language: Optional[str] = "en"
    crawl_timeout_ms: int = Field(default=15000, ge=1000, le=60000)


class PipelineResultItem(BaseModel):
    url: str
    title: Optional[str] = None
    score: float = Field(description="Reranker relevance score")
    markdown: str = Field(description="Extracted clean markdown content")
    search_snippet: Optional[str] = Field(default=None, description="Original search snippet")
    is_youtube: bool = Field(default=False, description="True if this is a YouTube video result")
    video_id: Optional[str] = Field(default=None, description="YouTube video ID")
    transcript_source: Optional[str] = Field(default=None, description="'youtube_subtitles' or 'whisper'")


class PipelineResponse(BaseModel):
    query: str
    results: list[PipelineResultItem]
    total_searched: int
    total_crawled: int
    timings: dict[str, float] = Field(default_factory=dict, description="Step timings in seconds")


# ── Pipeline Streaming (SSE) ───────────────────────────────────────────────


class PipelineStreamEvent(BaseModel):
    """A single SSE event emitted during the streaming pipeline."""
    event: Literal[
        "search",
        "crawl_start",
        "crawl_result",
        "crawl_error",
        "rerank",
        "result",
        "done",
        "error",
    ]
    data: Any = None


# ── Storage (MinIO / S3) ───────────────────────────────────────────────────


class StorageUploadRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=1024, description="Object key/path")
    bucket: Optional[str] = None
    content_type: Optional[str] = None


class StorageUploadResponse(BaseModel):
    bucket: str
    key: str
    size: int
    url: str


class StorageListRequest(BaseModel):
    prefix: Optional[str] = ""
    bucket: Optional[str] = None


class StorageFileItem(BaseModel):
    key: str
    size: Optional[int] = None
    last_modified: Optional[str] = None
    etag: Optional[str] = None


class StorageListResponse(BaseModel):
    bucket: str
    prefix: str
    files: list[StorageFileItem]
    count: int


class StorageDeleteRequest(BaseModel):
    keys: list[str] = Field(..., min_length=1, max_length=100)
    bucket: Optional[str] = None


class StorageDeleteResponse(BaseModel):
    bucket: str
    deleted: int
    errors: Optional[list[str]] = None


# ── News Search ────────────────────────────────────────────────────────────


class NewsSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int = Field(default=10, ge=1, le=50)
    region: str = Field(default="wt-wt", description="Region code, e.g. us-en, wt-wt")
    safesearch: str = Field(default="moderate", description="on, moderate, off")
    timelimit: Optional[str] = Field(default=None, description="d, w, m, y")
    crawl_content: bool = Field(default=False, description="Crawl full article content")
    crawl_timeout_ms: int = Field(default=15000, ge=1000, le=60000)


class NewsResultItem(BaseModel):
    title: str
    url: str
    source: Optional[str] = None
    published: Optional[str] = None
    body: Optional[str] = None
    image_url: Optional[str] = None
    crawled_content: Optional[str] = Field(default=None, description="Full article markdown content")


class NewsSearchResponse(BaseModel):
    query: str
    number_of_results: int
    results: list[NewsResultItem]
    timings: dict[str, float] = Field(default_factory=dict)


# ── Image Search ───────────────────────────────────────────────────────────


class ImageSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int = Field(default=10, ge=1, le=50)
    region: str = Field(default="wt-wt")
    safesearch: str = Field(default="moderate", description="on, moderate, off")
    size: Optional[str] = Field(default=None, description="Small, Medium, Large, Wallpaper")
    color: Optional[str] = Field(default=None, description="color, monochrome, transparent, red, orange, etc.")
    type_image: Optional[str] = Field(default=None, description="photo, clipart, gif, transparent, line")
    layout: Optional[str] = Field(default=None, description="Square, Tall, Wide")
    license_image: Optional[str] = Field(default=None, description="Any, Public, Share, ShareCommercially, Modify, ModifyCommercially")
    use_clip: bool = Field(default=True, description="Use CLIP to rerank images by relevance")


class ImageResultItem(BaseModel):
    title: str
    image_url: str
    thumbnail_url: Optional[str] = None
    source_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    clip_score: Optional[float] = Field(default=None, description="CLIP similarity score vs query")
    engine: Optional[str] = Field(default=None, description="Source engine: ddgs, unsplash, pexels")


class ImageSearchResponse(BaseModel):
    query: str
    number_of_results: int
    results: list[ImageResultItem]
    timings: dict[str, float] = Field(default_factory=dict)
    clip_enabled: bool = False


# ── Video Search ───────────────────────────────────────────────────────────


class VideoSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int = Field(default=10, ge=1, le=50)
    region: str = Field(default="wt-wt")
    safesearch: str = Field(default="moderate", description="on, moderate, off")
    timelimit: Optional[str] = Field(default=None, description="d, w, m, y")
    resolution: Optional[str] = Field(default=None, description="high, standard")
    duration: Optional[str] = Field(default=None, description="short, medium, long")
    license_video: Optional[str] = Field(default=None, description="creativeCommon, youtube")


class VideoResultItem(BaseModel):
    title: str
    url: str
    publisher: Optional[str] = None
    duration: Optional[str] = None
    views: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published: Optional[str] = None
    description: Optional[str] = None
    engine: str = "ddgs"


class VideoSearchResponse(BaseModel):
    query: str
    number_of_results: int
    results: list[VideoResultItem]
    timings: dict[str, float] = Field(default_factory=dict)
