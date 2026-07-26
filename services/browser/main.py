from fastapi import FastAPI

from routers.browser import router as browser_router

app = FastAPI(title="Browser API", description="Browser automation via Camoufox + Playwright", version="1.0.0")

app.include_router(browser_router, tags=["browser"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "browser"}
