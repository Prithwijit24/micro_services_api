from fastapi import FastAPI

from routers.cache import router as cache_router
from service import cache_service

app = FastAPI(title="Cache API", description="Cache API wrapping Redis", version="1.0.0")

app.include_router(cache_router, tags=["cache"])


@app.on_event("shutdown")
async def shutdown():
    await cache_service.close()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cache"}
