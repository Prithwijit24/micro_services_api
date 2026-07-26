from fastapi import FastAPI

from routers.embed import router as embed_router

app = FastAPI(title="Embed API", description="Text embeddings via BAAI/bge-small-en-v1.5", version="1.0.0")

app.include_router(embed_router, tags=["embed"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "embed"}
