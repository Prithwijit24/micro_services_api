"""Text embedding service via sentence-transformers."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.deps import get_embed_model
from app.models import EmbedRequest, EmbedResponse

_executor = ThreadPoolExecutor(max_workers=2)

class EmbedService:
    def _encode(self, texts: list[str], normalize: bool):
        model = get_embed_model()
        vectors = model.encode(texts, normalize_embeddings=normalize)
        return vectors.tolist(), model.get_embedding_dimension()

    async def embed(self, req: EmbedRequest) -> EmbedResponse:
        import os

        model_name = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        loop = asyncio.get_event_loop()
        vectors, dims = await loop.run_in_executor(_executor, self._encode, req.texts, req.normalize)
        return EmbedResponse(model=model_name, dimensions=dims, embeddings=vectors)
