import os
import httpx

SERVICE_URLS = {
    "search": os.getenv("SEARCH_SERVICE_URL", "http://search:8000"),
    "crawl": os.getenv("CRAWL_SERVICE_URL", "http://crawl:8000"),
    "browser": os.getenv("BROWSER_SERVICE_URL", "http://browser:8000"),
    "youtube": os.getenv("YOUTUBE_SERVICE_URL", "http://youtube:8000"),
    "embed": os.getenv("EMBED_SERVICE_URL", "http://embed:8000"),
    "clip": os.getenv("CLIP_SERVICE_URL", "http://clip:8000"),
    "reranker": os.getenv("RERANKER_SERVICE_URL", "http://reranker:8000"),
    "graph": os.getenv("GRAPH_SERVICE_URL", "http://graph:8000"),
    "vector": os.getenv("VECTOR_SERVICE_URL", "http://vector:8000"),
    "cache": os.getenv("CACHE_SERVICE_URL", "http://cache:8000"),
}

REQUEST_TIMEOUT = float(os.getenv("GATEWAY_UPSTREAM_TIMEOUT", "60"))


class GatewayService:
    """Thin reverse-proxy layer: forwards requests to internal microservices
    over the Docker network so external clients only ever talk to the gateway."""

    async def proxy(self, service: str, path: str, method: str, json_body=None, params=None) -> httpx.Response:
        base_url = SERVICE_URLS[service]
        url = f"{base_url}{path}"
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            return await client.request(method, url, json=json_body, params=params)

    async def check_health(self, service: str) -> tuple[str, str | None]:
        base_url = SERVICE_URLS[service]
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/health")
                if resp.status_code == 200:
                    return "ok", None
                return "degraded", f"HTTP {resp.status_code}"
        except Exception as e:
            return "unreachable", str(e)


gateway_service = GatewayService()
