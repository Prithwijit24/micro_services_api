from fastapi import FastAPI

from routers.reranker import router as reranker_router

app = FastAPI(title="Reranker API", description="Document reranking via BAAI/bge-reranker-v2-m3", version="1.0.0")

app.include_router(reranker_router, tags=["reranker"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "reranker"}
