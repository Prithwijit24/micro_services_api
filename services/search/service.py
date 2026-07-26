import os
import httpx

from models import SearchRequest, SearchResponse, SearchResultItem

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")


class SearchService:
    def __init__(self, base_url: str = SEARXNG_URL):
        self.base_url = base_url.rstrip("/")

    async def search(self, req: SearchRequest) -> SearchResponse:
        params = {
            "q": req.query,
            "format": "json",
            "categories": req.categories,
            "language": req.language,
            "safesearch": req.safesearch,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        raw_results = data.get("results", [])[: req.max_results]
        results = [
            SearchResultItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content"),
                engine=r.get("engine"),
            )
            for r in raw_results
        ]
        return SearchResponse(
            query=req.query,
            number_of_results=len(results),
            results=results,
        )


search_service = SearchService()
