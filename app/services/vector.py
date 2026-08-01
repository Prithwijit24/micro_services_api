"""Vector database service via ChromaDB."""

import os
import logging

import chromadb

from app.models import (
    UpsertRequest,
    UpsertResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    SearchMatch,
    VectorDeleteRequest,
    VectorDeleteResponse,
)

logger = logging.getLogger("vector")

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))


class VectorService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        return self._client

    def _get_collection(self, name: str, allow_create: bool = False):
        client = self._get_client()
        if allow_create:
            return client.get_or_create_collection(name=name)
        return client.get_collection(name=name)

    async def upsert(self, req: UpsertRequest) -> UpsertResponse:
        collection = self._get_collection(req.collection, allow_create=True)
        collection.upsert(
            ids=[r.id for r in req.records],
            embeddings=[r.embedding for r in req.records],
            documents=[r.document or "" for r in req.records],
            metadatas=[r.metadata for r in req.records],
        )
        return UpsertResponse(collection=req.collection, upserted=len(req.records))

    async def search(self, req: VectorSearchRequest) -> VectorSearchResponse:
        collection = self._get_collection(req.collection, allow_create=False)
        result = collection.query(
            query_embeddings=[req.query_embedding],
            n_results=req.top_k,
            where=req.where,
        )
        matches = []
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        for i in range(len(ids)):
            matches.append(
                SearchMatch(
                    id=ids[i],
                    score=distances[i],
                    document=documents[i] if documents else None,
                    metadata=metadatas[i] if metadatas else {},
                )
            )
        return VectorSearchResponse(collection=req.collection, matches=matches)

    async def delete(self, req: VectorDeleteRequest) -> VectorDeleteResponse:
        collection = self._get_collection(req.collection, allow_create=True)
        collection.delete(ids=req.ids)
        return VectorDeleteResponse(collection=req.collection, deleted=len(req.ids))
