"""CLIP embedding service via HuggingFace transformers."""

import asyncio
import base64
import io
import logging
from concurrent.futures import ThreadPoolExecutor

from urllib.request import urlopen

from app.deps import get_clip_model
from app.models import (
    TextEmbeddingRequest,
    ImageEmbeddingRequest,
    ClipEmbeddingResponse,
    SimilarityRequest,
    SimilarityResponse,
)

logger = logging.getLogger("clip")

_executor = ThreadPoolExecutor(max_workers=2)


class ClipService:
    def _load_images(self, image_urls, images_base64):
        from PIL import Image

        images = []
        if image_urls:
            for url in image_urls:
                with urlopen(url, timeout=20) as resp:
                    images.append(Image.open(io.BytesIO(resp.read())).convert("RGB"))
        if images_base64:
            for b64 in images_base64:
                images.append(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"))
        return images

    def _text_embed(self, texts: list[str]):
        model, processor = get_clip_model()
        inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True)
        outputs = model.get_text_features(**inputs)
        vecs = outputs.pooler_output.detach().cpu().numpy()
        return vecs.tolist(), vecs.shape[-1]

    def _image_embed(self, image_urls, images_base64):
        model, processor = get_clip_model()
        images = self._load_images(image_urls, images_base64)
        inputs = processor(images=images, return_tensors="pt")
        outputs = model.get_image_features(**inputs)
        vecs = outputs.pooler_output.detach().cpu().numpy()
        return vecs.tolist(), vecs.shape[-1]

    def _similarity(self, text: str, image_urls, images_base64):
        import torch

        model, processor = get_clip_model()
        images = self._load_images(image_urls, images_base64)
        inputs = processor(text=[text], images=images, return_tensors="pt", padding=True)
        outputs = model(**inputs)
        logits_per_image = outputs.logits_per_image
        scores = torch.nn.functional.softmax(logits_per_image, dim=0).squeeze(-1).detach().cpu().numpy()
        return scores.tolist()

    async def text_embedding(self, req: TextEmbeddingRequest) -> ClipEmbeddingResponse:
        import os

        model_name = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
        loop = asyncio.get_event_loop()
        vecs, dims = await loop.run_in_executor(_executor, self._text_embed, req.texts)
        return ClipEmbeddingResponse(model=model_name, dimensions=dims, embeddings=vecs)

    async def image_embedding(self, req: ImageEmbeddingRequest) -> ClipEmbeddingResponse:
        import os

        model_name = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
        loop = asyncio.get_event_loop()
        vecs, dims = await loop.run_in_executor(
            _executor, self._image_embed, req.image_urls, req.images_base64
        )
        return ClipEmbeddingResponse(model=model_name, dimensions=dims, embeddings=vecs)

    async def similarity(self, req: SimilarityRequest) -> SimilarityResponse:
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            _executor, self._similarity, req.text, req.image_urls, req.images_base64
        )
        return SimilarityResponse(text=req.text, scores=scores)
