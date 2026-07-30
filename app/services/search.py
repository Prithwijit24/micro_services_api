"""Search service — SearXNG or DuckDuckGo (DDGS), controlled via SEARCH_ENGINE config."""

import os
import asyncio
import logging

from app.deps import get_http_client
from app.models import SearchRequest, SearchResponse, SearchResultItem

logger = logging.getLogger("search")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
SEARCH_ENGINE = os.getenv("SEARCH_ENGINE", "searxng")


class SearchService:
    async def search(self, req: SearchRequest) -> SearchResponse:
        """Try primary engine first, fall back to secondary on failure."""
        primary, secondary = ("ddgs", "searxng") if SEARCH_ENGINE == "ddgs" else ("searxng", "ddgs")
        errors = []

        for engine in (primary, secondary):
            try:
                if engine == "ddgs":
                    return await self._search_ddgs(req)
                else:
                    return await self._search_searxng(req)
            except Exception as e:
                logger.warning("Search engine %s failed: %s", engine, e)
                errors.append(f"{engine}: {e}")

        raise Exception(f"All search engines failed: {'; '.join(errors)}")

    async def _search_searxng(self, req: SearchRequest) -> SearchResponse:
        client = get_http_client()
        resp = await client.get(
            f"{SEARXNG_URL}/search",
            params={
                "q": req.query,
                "format": "json",
                "categories": req.categories,
                "language": req.language,
                "safesearch": req.safesearch,
            },
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("results", [])[: req.max_results]
        results = [
            SearchResultItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content"),
                engine=r.get("engine"),
            )
            for r in raw
        ]
        return SearchResponse(query=req.query, number_of_results=len(results), results=results)

    async def _search_ddgs(self, req: SearchRequest) -> SearchResponse:
        from ddgs import DDGS

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None, self._ddgs_text, req.query, req.max_results
        )
        results = [
            SearchResultItem(
                title=r.get("title", ""),
                url=r.get("href", ""),
                content=r.get("body"),
                engine="ddgs",
            )
            for r in raw
        ]
        return SearchResponse(query=req.query, number_of_results=len(results), results=results)

    def _ddgs_text(self, query: str, max_results: int) -> list[dict]:
        from ddgs import DDGS

        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
