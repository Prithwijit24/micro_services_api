from fastapi import FastAPI

from routers.vector import router as vector_router

app = FastAPI(title="Vector API", description="Vector search API wrapping ChromaDB", version="1.0.0")

app.include_router(vector_router, tags=["vector"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vector"}
