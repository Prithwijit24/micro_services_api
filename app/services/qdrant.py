"""Qdrant vector database service."""

import os
import logging
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.models import (
    QdrantUpsertRequest,
    QdrantUpsertResponse,
    QdrantSearchRequest,
    QdrantSearchResponse,
    QdrantDeleteRequest,
    QdrantDeleteResponse,
    QdrantCreateCollectionRequest,
    QdrantCreateCollectionResponse,
    QdrantCollectionsResponse,
    SearchMatch,
)

logger = logging.getLogger("qdrant")

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))


class QdrantService:
    def __init__(self):
        self._client: Optional[QdrantClient] = None

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        return self._client

    _DISTANCE_MAP = {
        "Cosine": Distance.COSINE,
        "Euclid": Distance.EUCLID,
        "Dot": Distance.DOT,
        "Manhattan": Distance.MANHATTAN,
    }

    async def create_collection(self, req: QdrantCreateCollectionRequest) -> QdrantCreateCollectionResponse:
        client = self._get_client()
        collections = client.get_collections().collections
        exists = any(c.name == req.collection for c in collections)

        if not exists:
            distance = self._DISTANCE_MAP.get(req.distance, Distance.COSINE)
            client.create_collection(
                collection_name=req.collection,
                vectors_config=VectorParams(
                    size=req.dimensions,
                    distance=distance,
                ),
            )

        return QdrantCreateCollectionResponse(
            collection=req.collection,
            created=not exists,
            dimensions=req.dimensions,
        )

    async def list_collections(self) -> QdrantCollectionsResponse:
        client = self._get_client()
        collections = client.get_collections().collections
        return QdrantCollectionsResponse(
            collections=[c.name for c in collections]
        )

    async def upsert(self, req: QdrantUpsertRequest) -> QdrantUpsertResponse:
        client = self._get_client()

        points = [
            PointStruct(
                id=r.id,
                vector=r.embedding,
                payload={
                    **(r.metadata or {}),
                    "document": r.document or "",
                },
            )
            for r in req.records
        ]

        client.upsert(collection_name=req.collection, points=points)

        return QdrantUpsertResponse(
            collection=req.collection,
            upserted=len(req.records),
        )

    async def search(self, req: QdrantSearchRequest) -> QdrantSearchResponse:
        client = self._get_client()

        query_filter = None
        if req.where:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in req.where.items()
            ]
            query_filter = Filter(must=conditions)

        results = client.search(
            collection_name=req.collection,
            query_vector=req.query_embedding,
            limit=req.top_k,
            query_filter=query_filter,
        )

        matches = [
            SearchMatch(
                id=str(r.id),
                score=r.score,
                document=(r.payload or {}).get("document"),
                metadata={k: v for k, v in (r.payload or {}).items() if k != "document"},
            )
            for r in results
        ]

        return QdrantSearchResponse(
            collection=req.collection,
            matches=matches,
        )

    async def delete(self, req: QdrantDeleteRequest) -> QdrantDeleteResponse:
        client = self._get_client()
        client.delete(
            collection_name=req.collection,
            points_selector=req.ids,
        )

        return QdrantDeleteResponse(
            collection=req.collection,
            deleted=len(req.ids),
        )


qdrant_service = QdrantService()
