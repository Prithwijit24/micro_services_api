"""Search service — 4-layer fallback chain: DDGS → SearXNG → Tavily → SerpAPI."""

import os
import asyncio
import logging

from app.deps import get_http_client
from app.models import SearchRequest, SearchResponse, SearchResultItem

logger = logging.getLogger("search")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")    # https://tavily.com (free tier available)
SERPAPI_API_KEY = os.getenv("SERP_API_KEY", "")  # https://serpapi.com (free tier available)

# Engine chain in priority order
_ENGINE_CHAIN = ["ddgs", "searxng", "tavily", "serpapi"]


class SearchService:
    async def search(self, req: SearchRequest) -> SearchResponse:
        """Try engines in priority order: DDGS → SearXNG → Tavily → SerpAPI."""
        errors = []

        for engine in _ENGINE_CHAIN:
            try:
                if engine == "ddgs":
                    return await self._search_ddgs(req)
                elif engine == "searxng":
                    return await self._search_searxng(req)
                elif engine == "tavily":
                    return await self._search_tavily(req)
                elif engine == "serpapi":
                    return await self._search_serpapi(req)
            except Exception as e:
                logger.warning("Search engine %s failed: %s", engine, e)
                errors.append(f"{engine}: {e}")

        raise Exception(f"All search engines failed: {'; '.join(errors)}")

    # ── DDGS ──────────────────────────────────────────────────────────────

    async def _search_ddgs(self, req: SearchRequest) -> SearchResponse:
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

    # ── SearXNG ───────────────────────────────────────────────────────────

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

    # ── Tavily ────────────────────────────────────────────────────────────

    async def _search_tavily(self, req: SearchRequest) -> SearchResponse:
        if not TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY not configured")

        client = get_http_client()
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": req.query,
                "search_depth": "basic",
                "max_results": req.max_results,
                "include_answer": False,
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
                engine="tavily",
            )
            for r in raw
        ]
        return SearchResponse(query=req.query, number_of_results=len(results), results=results)

    # ── SerpAPI ───────────────────────────────────────────────────────────

    async def _search_serpapi(self, req: SearchRequest) -> SearchResponse:
        if not SERPAPI_API_KEY:
            raise RuntimeError("SERPAPI_API_KEY not configured")

        client = get_http_client()
        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "api_key": SERPAPI_API_KEY,
                "q": req.query,
                "engine": "google",
                "num": req.max_results,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        # SerpAPI returns organic_results directly
        raw = data.get("organic_results", [])

        results = []
        # Add knowledge graph if present
        kg = data.get("knowledge_graph", {})
        answer_box = data.get("answer_box", {})
        if kg:
            title = kg.get("title", "")
            url = kg.get("source", {}).get("link", "") if isinstance(kg.get("source"), dict) else kg.get("website", "")
            desc = kg.get("description", "")
            if title or desc:
                results.append(SearchResultItem(
                    title=title or "Knowledge Graph",
                    url=url or "",
                    content=desc,
                    engine="serpapi",
                ))
        # Add answer box if present
        if answer_box:
            title = answer_box.get("title", "")
            url = answer_box.get("link", "")
            snippet = answer_box.get("snippet") or answer_box.get("answer", "")
            if title or snippet:
                results.append(SearchResultItem(
                    title=title or "Answer Box",
                    url=url or "",
                    content=snippet,
                    engine="serpapi",
                ))
        # Add organic results, then trim to max_results
        for r in raw:
            results.append(SearchResultItem(
                title=r.get("title", ""),
                url=r.get("link", ""),
                content=r.get("snippet"),
                engine="serpapi",
            ))
        results = results[: req.max_results]
        return SearchResponse(query=req.query, number_of_results=len(results), results=results)
