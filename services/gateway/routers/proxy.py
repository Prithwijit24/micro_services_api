from fastapi import APIRouter, Request, HTTPException, Response
import httpx

from service import gateway_service, SERVICE_URLS

router = APIRouter()

# Maps external gateway path prefixes to (internal service name, path is forwarded verbatim)
ROUTE_MAP = {
    "/search": "search",
    "/crawl": "crawl",
    "/browse": "browser",
    "/youtube": "youtube",
    "/embed": "embed",
    "/clip": "clip",
    "/rerank": "reranker",
    "/graph": "graph",
    "/vector": "vector",
    "/cache": "cache",
}


@router.api_route("/{full_path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
async def proxy_request(full_path: str, request: Request):
    path = f"/{full_path}"
    service = None
    for prefix, svc in ROUTE_MAP.items():
        if path == prefix or path.startswith(prefix + "/"):
            service = svc
            break

    if service is None:
        raise HTTPException(status_code=404, detail="No matching service route")

    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = None

    try:
        upstream_resp = await gateway_service.proxy(
            service=service,
            path=path,
            method=request.method,
            json_body=body,
            params=dict(request.query_params),
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream '{service}' error: {e}")

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        media_type=upstream_resp.headers.get("content-type", "application/json"),
    )
