import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from models import RerankRequest, RerankResponse, RerankedDocument

logger = logging.getLogger("reranker")

MODEL_NAME = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
_executor = ThreadPoolExecutor(max_workers=2)


class RerankerService:
    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading reranker model %s", MODEL_NAME)
            self._model = CrossEncoder(MODEL_NAME, cache_folder=os.getenv("HF_HOME"))
        return self._model

    def _rerank(self, query: str, documents: list[str], top_k: int | None):
        model = self._load()
        pairs = [[query, doc] for doc in documents]
        scores = model.predict(pairs)
        ranked = sorted(
            [(i, documents[i], float(scores[i])) for i in range(len(documents))],
            key=lambda x: x[2],
            reverse=True,
        )
        if top_k:
            ranked = ranked[:top_k]
        return ranked

    async def rerank(self, req: RerankRequest) -> RerankResponse:
        loop = asyncio.get_event_loop()
        ranked = await loop.run_in_executor(_executor, self._rerank, req.query, req.documents, req.top_k)
        results = [RerankedDocument(index=i, document=d, score=s) for i, d, s in ranked]
        return RerankResponse(model=MODEL_NAME, query=req.query, results=results)


reranker_service = RerankerService()
