from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import PipelineRequest, PipelineResponse
from app.services.pipeline import pipeline_service

router = APIRouter()


@router.post("/pipeline", response_model=PipelineResponse)
async def pipeline(req: PipelineRequest):
    """Search the web, crawl top results, and rerank by relevance — all in one call."""
    try:
        return await pipeline_service.run(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/stream")
async def pipeline_stream(req: PipelineRequest):
    """Streaming version: results arrive as SSE events as each URL is crawled.

    Events:
      - search       : search completed
      - crawl_start  : crawling begins
      - crawl_result : one URL crawled successfully
      - crawl_error  : one URL failed
      - rerank       : reranking in progress
      - result       : one ranked result
      - done         : pipeline complete
      - error        : unrecoverable error
    """
    return StreamingResponse(
        pipeline_service.run_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
