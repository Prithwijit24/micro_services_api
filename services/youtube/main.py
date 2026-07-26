from fastapi import FastAPI

from routers.youtube import router as youtube_router

app = FastAPI(title="YouTube API", description="YouTube download/info/transcript via yt-dlp", version="1.0.0")

app.include_router(youtube_router, tags=["youtube"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "youtube"}
