"""News service — DDGS news search with optional crawl fallback for full articles."""

import asyncio
import time
import logging

from app.models import NewsSearchRequest, NewsSearchResponse, NewsResultItem, CrawlRequest
from app.services.crawl import CrawlService

logger = logging.getLogger("news")

# Timeout for DDGS extract in news crawl (seconds)
_NEWS_DDGS_EXTRACT_TIMEOUT = 10.0


class NewsService:
    """Search news via DDGS, optionally crawl full article content."""

    def __init__(self):
        self.crawl = CrawlService()

    async def search(self, req: NewsSearchRequest) -> NewsSearchResponse:
        timings: dict[str, float] = {}
        errors: list[str] = []

        # ── Step 1: DDGS News Search ───────────────────────────────────
        t0 = time.time()
        raw = await self._search_ddgs(req)
        timings["search"] = round(time.time() - t0, 2)

        crawled_content: dict[int, str] = {}

        if not raw:
            return NewsSearchResponse(
                query=req.query, number_of_results=0, results=[], timings=timings,
            )

        # ── Step 2: Optionally crawl full articles ─────────────────────
        if req.crawl_content:
            t1 = time.time()
            semaphore = asyncio.Semaphore(5)

            async def _crawl_one(item, index: int):
                async with semaphore:
                    url = item.get("url", "")
                    if not url:
                        return index, None

                    # Layer 1: Fast DDGS extract (with timeout)
                    try:
                        md = await asyncio.wait_for(
                            self._ddgs_extract(url),
                            timeout=_NEWS_DDGS_EXTRACT_TIMEOUT
                        )
                        if md and len(md.strip()) >= 50:
                            return index, md.strip()
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug("DDGS extract failed for %s: %s", url, e)

                    # Layer 2: Full CrawlService chain (Scrapling → Trafilatura → ...)
                    try:
                        crawl_result = await self.crawl.crawl(
                            CrawlRequest(
                                url=url,
                                only_main_content=True,
                                include_html=False,
                                timeout_ms=req.crawl_timeout_ms,
                            )
                        )
                        md = crawl_result.markdown.strip()
                        return index, md if md else None
                    except Exception as e:
                        logger.warning("News crawl failed for %s: %s", url, e)
                        return index, None

            tasks = [
                asyncio.create_task(_crawl_one(item, i))
                for i, item in enumerate(raw)
            ]

            crawled_content = {}
            for coro in asyncio.as_completed(tasks):
                idx, content = await coro
                if content:
                    crawled_content[idx] = content

            timings["crawl"] = round(time.time() - t1, 2)

        # ── Step 3: Build results ──────────────────────────────────────
        results = []
        for i, item in enumerate(raw):
            result = NewsResultItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source=item.get("source"),
                published=item.get("date"),
                body=item.get("body"),
                image_url=item.get("image"),
                crawled_content=crawled_content.get(i) if req.crawl_content else None,
            )
            results.append(result)

        timings["total"] = round(sum(timings.values()), 2)

        return NewsSearchResponse(
            query=req.query,
            number_of_results=len(results),
            results=results,
            timings=timings,
        )

    async def _search_ddgs(self, req: NewsSearchRequest) -> list[dict]:
        from ddgs import DDGS

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None,
            self._ddgs_news,
            req.query,
            req.max_results,
            req.region,
            req.safesearch,
            req.timelimit,
        )
        return raw

    async def _ddgs_extract(self, url: str) -> str | None:
        """Extract article content via DDGS extract. Returns markdown or None."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._ddgs_extract_sync, url)

    def _ddgs_extract_sync(self, url: str) -> str | None:
        from ddgs import DDGS

        with DDGS() as ddgs:
            data = ddgs.extract(url, fmt="text_markdown")
        content = data.get("content", "")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        markdown = content if isinstance(content, str) else str(content)
        return markdown if markdown.strip() else None

    def _ddgs_news(self, query: str, max_results: int, region: str,
                   safesearch: str, timelimit: str | None) -> list[dict]:
        from ddgs import DDGS

        kwargs = {
            "query": query,
            "region": region,
            "safesearch": safesearch,
            "max_results": max_results,
        }
        if timelimit:
            kwargs["timelimit"] = timelimit

        with DDGS() as ddgs:
            return list(ddgs.news(**kwargs))


news_service = NewsService()
