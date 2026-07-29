from fastapi import FastAPI

from app.routers import register_all_routers

app = FastAPI(
    title="AI Infra Stack",
    description="Unified API for search, browse, embed, and more",
    version="2.0.0",
)

register_all_routers(app)


@app.get("/health")
async def health():
    return {"status": "ok"}
