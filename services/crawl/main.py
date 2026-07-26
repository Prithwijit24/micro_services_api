from fastapi import FastAPI

from routers.crawl import router as crawl_router

app = FastAPI(title="Crawl API", description="Web crawling via Firecrawl", version="1.0.0")

app.include_router(crawl_router, tags=["crawl"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "crawl"}
