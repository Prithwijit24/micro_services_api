from fastapi import FastAPI

from routers.search import router as search_router

app = FastAPI(title="Search API", description="Web search via SearXNG", version="1.0.0")

app.include_router(search_router, tags=["search"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "search"}
