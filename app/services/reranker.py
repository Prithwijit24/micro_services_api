"""Reranker service via sentence-transformers CrossEncoder."""

import asyncio
from app.services.executors import ManagedExecutor
from app.deps import get_reranker_model
from app.models import RerankRequest, RerankResponse, RerankedDocument

import os

_executor = ManagedExecutor(2, "reranker")


class RerankerService:
    def _rerank(self, query: str, documents: list[str], top_k: int | None):
        model = get_reranker_model()
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
        model_name = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
        loop = asyncio.get_event_loop()
        ranked = await loop.run_in_executor(
            _executor.get(), self._rerank, req.query, req.documents, req.top_k
        )
        results = [RerankedDocument(index=i, document=d, score=s) for i, d, s in ranked]
        return RerankResponse(model=model_name, query=req.query, results=results)


def close() -> None:
    _executor.close()
