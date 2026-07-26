from fastapi import FastAPI

from routers.clip import router as clip_router

app = FastAPI(title="CLIP API", description="Text/image embeddings via openai/clip-vit-base-patch32", version="1.0.0")

app.include_router(clip_router, tags=["clip"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "clip"}
