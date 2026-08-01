"""Pipeline service: Search → Crawl → Rerank in one call (with streaming support).

YouTube video results are automatically detected and transcribed via Whisper
instead of being crawled, so video content participates in reranking.
"""

import os
import asyncio
import json
import re
import time
import logging
from datetime import timedelta
from dataclasses import dataclass
from typing import AsyncGenerator

from app.models import (
    PipelineRequest,
    PipelineResponse,
    PipelineResultItem,
    PipelineStreamEvent,
    SearchRequest,
    CrawlRequest,
    RerankRequest,
)
from app.services.search import SearchService
from app.services.crawl import CrawlService
from app.services.reranker import RerankerService
from app.services.youtube import YoutubeService

# Reuse the YouTube service's thread pool for transcript extraction
from app.services.youtube import _executor as _yt_executor

logger = logging.getLogger("pipeline")

# Concurrency limit for crawling to avoid overwhelming target servers
_CRAWL_SEMAPHORE_LIMIT = 5

# YouTube transcript timeout (seconds) — bounds caller wait, not thread cancellation
PIPELINE_YT_TIMEOUT = int(os.getenv("PIPELINE_YT_TIMEOUT", "120"))

# YouTube URL patterns
_YT_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?'
    r'(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/|'
    r'youtube\.com/shorts/|youtube\.com/live/)'
    r'([\w-]{11})',
    re.IGNORECASE,
)


def _is_youtube_url(url: str) -> bool:
    """Return True if the URL is a YouTube video URL."""
    return bool(_YT_PATTERN.search(url))


def _extract_yt_id(url: str) -> str | None:
    """Extract the 11-char YouTube video ID from a URL."""
    m = _YT_PATTERN.search(url)
    return m.group(1) if m else None


@dataclass
class CrawledItem:
    """Holds the result of crawling a single URL."""
    url: str
    title: str
    markdown: str
    search_snippet: str
    is_youtube: bool = False
    video_id: str | None = None
    transcript_source: str | None = None  # 'youtube_subtitles' or 'whisper'


def _sse(event: PipelineStreamEvent) -> str:
    """Format a PipelineStreamEvent as an SSE string."""
    payload = event.model_dump()
    return f"event: {payload['event']}\ndata: {json.dumps(payload['data'], default=str)}\n\n"


class PipelineService:
    """Orchestrates Search → Crawl → Rerank into a single pipeline."""

    def __init__(self):
        self.search = SearchService()
        self.crawl = CrawlService()
        self.reranker = RerankerService()
        self.youtube = YoutubeService()

    # ── Non-streaming (original) ──────────────────────────────────────────

    async def _fetch_youtube_transcript(self, item, language: str = "en") -> CrawledItem:
        """Fetch YouTube transcript for a video URL (subtitles first, Whisper fallback).

        Note: asyncio.wait_for only bounds the *caller's* wait. The executor thread
        continues until _extract_transcript finishes, holding the semaphore slot.
        """
        loop = asyncio.get_running_loop()
        video_id = _extract_yt_id(item.url)
        try:
            # Use shared _executor from youtube.py for consistency
            data = await asyncio.wait_for(
                loop.run_in_executor(
                    _yt_executor.get(), self.youtube._extract_transcript, item.url, language, False
                ),
                timeout=PIPELINE_YT_TIMEOUT,
            )
            segments = data.get("segments", [])

            # Build markdown with timestamps for richer reranker context
            lines = []
            for seg in segments:
                start = seg.get("start", 0)
                text = seg.get("text", "").strip()
                if text:
                    ts = str(timedelta(seconds=int(start)))
                    lines.append(f"**[{ts}]** {text}")
            transcript_text = "\n".join(lines)

            if not transcript_text:
                raise RuntimeError("Empty transcript")

            source = data.get("source", "unknown")
            source_label = "YouTube Subtitles" if source == "youtube_subtitles" else f"Whisper ({data.get('whisper_model', 'N/A')})"

            return CrawledItem(
                url=item.url,
                title=item.title or f"YouTube Video {video_id}",
                markdown=f"# {item.title or 'YouTube Video'}\n\n**Source:** {source_label}\n\n{transcript_text}",
                search_snippet=item.content or "\n".join(
                    seg.get("text", "").strip() for seg in segments[:10] if seg.get("text", "").strip()
                ),
                is_youtube=True,
                video_id=video_id,
                transcript_source=source,
            )
        except Exception as e:
            logger.warning("YouTube transcript failed for %s [%s]: %s", item.url, type(e).__name__, e)
            return CrawledItem(
                url=item.url,
                title=item.title or f"YouTube Video {video_id}",
                markdown=item.content or f"YouTube video: {item.title}\n\n[Transcript unavailable: {e}]",
                search_snippet=item.content or "",
                is_youtube=True,
                video_id=video_id,
            )

    async def _process_item(self, item, semaphore: asyncio.Semaphore, timeout_ms: int):
        """Process one search result for both normal and streaming pipelines."""
        async with semaphore:
            if _is_youtube_url(item.url):
                try:
                    return await self._fetch_youtube_transcript(item), None, "youtube"
                except Exception as exc:
                    logger.warning("YouTube transcript failed for %s [%s]: %s", item.url, type(exc).__name__, exc)
                    return None, f"YouTube transcript failed for {item.url}: {exc}", "youtube"

            try:
                result = await self.crawl.crawl(
                    CrawlRequest(
                        url=item.url,
                        only_main_content=True,
                        include_html=False,
                        timeout_ms=timeout_ms,
                    )
                )
                markdown = result.markdown.strip()
                if markdown:
                    return CrawledItem(
                        url=result.url,
                        title=result.title or item.title or "",
                        markdown=markdown,
                        search_snippet=item.content or "",
                    ), None, "crawl"
                if item.content:
                    return CrawledItem(
                        url=result.url,
                        title=result.title or item.title or "",
                        markdown=item.content,
                        search_snippet=item.content or "",
                    ), None, "crawl"
                return None, f"Empty crawl result for {result.url}", "crawl"
            except Exception as exc:
                logger.warning("Crawl failed for %s [%s]: %s", item.url, type(exc).__name__, exc)
                if item.content:
                    return CrawledItem(
                        url=item.url,
                        title=item.title or "",
                        markdown=item.content,
                        search_snippet=item.content or "",
                    ), None, "crawl"
                return None, f"Crawl failed for {item.url}: {exc}", "crawl"

    async def run(self, req: PipelineRequest) -> PipelineResponse:
        timings: dict[str, float] = {}
        # ── Step 1: Search ────────────────────────────────────────────────
        t0 = time.time()
        search_resp = await self.search.search(
            SearchRequest(
                query=req.query,
                max_results=req.max_search_results,
                categories=req.categories,
                language=req.language,
            )
        )
        timings["search"] = round(time.time() - t0, 2)

        search_results = search_resp.results
        if not search_results:
            return PipelineResponse(
                query=req.query, results=[], total_searched=0,
                total_crawled=0, timings=timings,
            )

        urls_to_crawl = search_results[: req.crawl_limit]

        # ── Step 2: Crawl/Transcribe (concurrent with semaphore) ──────────
        t1 = time.time()
        semaphore = asyncio.Semaphore(_CRAWL_SEMAPHORE_LIMIT)

        results = await asyncio.gather(
            *(self._process_item(item, semaphore, req.crawl_timeout_ms) for item in urls_to_crawl)
        )
        crawled_items = [item for item, _, _ in results if item is not None]

        timings["crawl"] = round(time.time() - t1, 2)

        if not crawled_items:
            return PipelineResponse(
                query=req.query, results=[], total_searched=len(search_results),
                total_crawled=0, timings=timings,
            )

        # ── Step 3: Rerank ────────────────────────────────────────────────
        t2 = time.time()
        documents = [
            f"{item.title}: {item.markdown[:1500]}" if item.title else item.markdown[:1500]
            for item in crawled_items
        ]
        rerank_resp = await self.reranker.rerank(
            RerankRequest(query=req.query, documents=documents, top_k=req.top_k)
        )
        timings["rerank"] = round(time.time() - t2, 2)
        timings["total"] = round(sum(timings.values()), 2)

        results = []
        for ranked_doc in rerank_resp.results:
            idx = ranked_doc.index
            if idx < len(crawled_items):
                item = crawled_items[idx]
                result_data = {
                    "url": item.url, "title": item.title, "score": ranked_doc.score,
                    "markdown": item.markdown[:req.max_markdown_chars],
                    "search_snippet": item.search_snippet,
                    "is_youtube": item.is_youtube,
                    "video_id": item.video_id,
                    "transcript_source": item.transcript_source,
                }
                results.append(PipelineResultItem(**result_data))

        return PipelineResponse(
            query=req.query, results=results, total_searched=len(search_results),
            total_crawled=len(crawled_items), timings=timings,
        )

    # ── Streaming (SSE) ───────────────────────────────────────────────────

    async def run_stream(self, req: PipelineRequest) -> AsyncGenerator[str, None]:
        """Yields SSE events as the pipeline progresses.

        Events emitted:
          - search        : search completed, includes result count
          - crawl_start   : about to crawl/transcribe N URLs
          - crawl_result  : one URL crawled successfully (url, title, markdown snippet)
          - crawl_error   : one URL failed to crawl
          - rerank        : reranking in progress
          - result        : one final ranked result
          - done          : pipeline complete (timings summary)
          - error         : unrecoverable error
        """
        timings: dict[str, float] = {}

        # ── Step 1: Search ────────────────────────────────────────────────
        t0 = time.time()
        try:
            search_resp = await self.search.search(
                SearchRequest(
                    query=req.query,
                    max_results=req.max_search_results,
                    categories=req.categories,
                    language=req.language,
                )
            )
        except Exception as e:
            yield _sse(PipelineStreamEvent(event="error", data={"error": str(e)}))
            return

        timings["search"] = round(time.time() - t0, 2)

        search_results = search_resp.results
        yield _sse(PipelineStreamEvent(event="search", data={
            "query": req.query,
            "total_results": len(search_results),
            "timings": timings,
        }))

        if not search_results:
            yield _sse(PipelineStreamEvent(event="done", data={
                "total_searched": 0, "total_crawled": 0, "timings": timings,
            }))
            return

        urls_to_crawl = search_results[: req.crawl_limit]

        # ── Step 2: Crawl/Transcribe (concurrent, events as each completes) ─
        yield _sse(PipelineStreamEvent(event="crawl_start", data={
            "urls_count": len(urls_to_crawl),
            "urls": [item.url for item in urls_to_crawl],
        }))

        t1 = time.time()
        semaphore = asyncio.Semaphore(_CRAWL_SEMAPHORE_LIMIT)
        crawled_items: list[CrawledItem] = []

        async def _process_one_stream(item, index: int):
            crawled_item, error, source = await self._process_item(
                item, semaphore, req.crawl_timeout_ms
            )
            return crawled_item, index, error, source

        # Fire all concurrently, yield events as they complete
        tasks = [
            asyncio.create_task(_process_one_stream(item, i))
            for i, item in enumerate(urls_to_crawl)
        ]

        for coro in asyncio.as_completed(tasks):
            item, original_index, error, source = await coro
            if error:
                yield _sse(PipelineStreamEvent(event="crawl_error", data={
                    "url": urls_to_crawl[original_index].url,
                    "index": original_index,
                    "error": error,
                    "source": source,
                }))
            else:
                crawled_items.append(item)
                event_data = {
                    "url": item.url, "title": item.title,
                    "snippet": item.markdown[:300],
                    "index": original_index, "total_crawled": len(crawled_items),
                    "source": source,
                }
                if item.is_youtube:
                    event_data["is_youtube"] = True
                    event_data["video_id"] = item.video_id
                    event_data["transcript_source"] = item.transcript_source
                yield _sse(PipelineStreamEvent(event="crawl_result", data=event_data))

        timings["crawl"] = round(time.time() - t1, 2)

        if not crawled_items:
            yield _sse(PipelineStreamEvent(event="done", data={
                "total_searched": len(search_results), "total_crawled": 0,
                "timings": timings,
            }))
            return

        # ── Step 3: Rerank ────────────────────────────────────────────────
        t2 = time.time()
        yield _sse(PipelineStreamEvent(event="rerank", data={
            "documents_count": len(crawled_items),
        }))

        documents = [
            f"{item.title}: {item.markdown[:1500]}" if item.title else item.markdown[:1500]
            for item in crawled_items
        ]
        rerank_resp = await self.reranker.rerank(
            RerankRequest(query=req.query, documents=documents, top_k=req.top_k)
        )
        timings["rerank"] = round(time.time() - t2, 2)
        timings["total"] = round(sum(timings.values()), 2)

        # ── Emit final results one by one ─────────────────────────────────
        for ranked_doc in rerank_resp.results:
            idx = ranked_doc.index
            if idx < len(crawled_items):
                item = crawled_items[idx]
                result_data = {
                    "url": item.url, "title": item.title, "score": ranked_doc.score,
                    "markdown": item.markdown[:req.max_markdown_chars],
                    "search_snippet": item.search_snippet,
                    "is_youtube": item.is_youtube,
                    "video_id": item.video_id,
                    "transcript_source": item.transcript_source,
                }
                yield _sse(PipelineStreamEvent(event="result", data=result_data))

        # ── Done ──────────────────────────────────────────────────────────
        yield _sse(PipelineStreamEvent(event="done", data={
            "total_searched": len(search_results),
            "total_crawled": len(crawled_items),
            "timings": timings,
        }))


pipeline_service = PipelineService()
