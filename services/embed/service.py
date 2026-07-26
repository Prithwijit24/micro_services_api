import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from models import EmbedRequest, EmbedResponse

logger = logging.getLogger("embed")

MODEL_NAME = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
_executor = ThreadPoolExecutor(max_workers=2)


class EmbedService:
    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model %s", MODEL_NAME)
            self._model = SentenceTransformer(MODEL_NAME, cache_folder=os.getenv("HF_HOME"))
        return self._model

    def _encode(self, texts: list[str], normalize: bool):
        model = self._load_model()
        vectors = model.encode(texts, normalize_embeddings=normalize)
        return vectors.tolist(), model.get_sentence_embedding_dimension()

    async def embed(self, req: EmbedRequest) -> EmbedResponse:
        loop = asyncio.get_event_loop()
        vectors, dims = await loop.run_in_executor(_executor, self._encode, req.texts, req.normalize)
        return EmbedResponse(model=MODEL_NAME, dimensions=dims, embeddings=vectors)


embed_service = EmbedService()
