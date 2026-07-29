"""Search service — SearXNG or DuckDuckGo (DDGS), controlled via SEARCH_ENGINE config."""

import os
import asyncio

from app.deps import get_http_client
from app.models import SearchRequest, SearchResponse, SearchResultItem

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
SEARCH_ENGINE = os.getenv("SEARCH_ENGINE", "searxng")


class SearchService:
    async def search(self, req: SearchRequest) -> SearchResponse:
        if SEARCH_ENGINE == "ddgs":
            return await self._search_ddgs(req)
        return await self._search_searxng(req)

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
