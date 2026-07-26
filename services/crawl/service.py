import os
import httpx

from models import CrawlRequest, CrawlResponse

FIRECRAWL_URL = os.getenv("FIRECRAWL_URL", "http://firecrawl:3002")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")


class CrawlService:
    def __init__(self, base_url: str = FIRECRAWL_URL):
        self.base_url = base_url.rstrip("/")

    async def crawl(self, req: CrawlRequest) -> CrawlResponse:
        payload = {
            "url": str(req.url),
            "formats": ["markdown", "html"] if req.include_html else ["markdown"],
            "onlyMainContent": req.only_main_content,
            "timeout": req.timeout_ms,
        }
        headers = {}
        if FIRECRAWL_API_KEY:
            headers["Authorization"] = f"Bearer {FIRECRAWL_API_KEY}"

        async with httpx.AsyncClient(timeout=req.timeout_ms / 1000 + 5) as client:
            resp = await client.post(f"{self.base_url}/v1/scrape", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        d = data.get("data", data)
        return CrawlResponse(
            url=str(req.url),
            markdown=d.get("markdown", ""),
            html=d.get("html") if req.include_html else None,
            title=(d.get("metadata") or {}).get("title"),
            status_code=(d.get("metadata") or {}).get("statusCode"),
        )


crawl_service = CrawlService()
