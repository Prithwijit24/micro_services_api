"""CLIP embedding service via HuggingFace transformers."""

import asyncio
import base64
import io
import logging
import torch
from PIL import Image

from app.services.executors import ManagedExecutor
from app.deps import get_clip_model
from app.services.url_policy import safe_http_get
from app.models import (
    TextEmbeddingRequest,
    ImageEmbeddingRequest,
    ClipEmbeddingResponse,
    SimilarityRequest,
    SimilarityResponse,
)

logger = logging.getLogger("clip")

_executor = ManagedExecutor(2, "clip")


def _embedding_tensor(outputs):
    """Normalize CLIPModel.get_*_features output across transformers versions."""
    if isinstance(outputs, torch.Tensor):
        return outputs
    return outputs.pooler_output


class ClipService:
    def _load_images(self, image_urls, images_base64):
        images: list[Image.Image] = []
        url_failures = 0
        b64_failures = 0
        if image_urls:
            for url in image_urls:
                try:
                    resp = safe_http_get(
                        url,
                        timeout=20,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; AI-Infra-Stack/2.1)"},
                    )
                    resp.raise_for_status()
                    buf = io.BytesIO(resp.content)
                    with Image.open(buf) as im:
                        images.append(im.convert("RGB"))
                except Exception as e:
                    logger.warning("CLIP failed to download image %s: %s", url[:80], e)
                    url_failures += 1
        if images_base64:
            for idx, b64 in enumerate(images_base64):
                try:
                    buf = io.BytesIO(base64.b64decode(b64, validate=True))
                    with Image.open(buf) as im:
                        images.append(im.convert("RGB"))
                except Exception as exc:
                    logger.warning("CLIP failed to decode base64 image at index %d: %s", idx, exc)
                    b64_failures += 1
        if not images:
            only_b64_input = not image_urls
            all_b64_invalid = bool(images_base64) and b64_failures == len(images_base64)
            if only_b64_input and all_b64_invalid:
                raise ValueError("images_base64 contains invalid image data")
            raise ValueError(
                f"no usable images were provided (url_failures={url_failures}, b64_failures={b64_failures})"
            )
        if url_failures or b64_failures:
            logger.info(
                "CLIP _load_images: %d URL(s) skipped, %d base64 skipped",
                url_failures, b64_failures,
            )
        return images

    def _text_embed(self, texts: list[str]):
        model, processor = get_clip_model()
        inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True)
        outputs = model.get_text_features(**inputs)
        vecs = _embedding_tensor(outputs).detach().cpu().numpy()
        return vecs.tolist(), vecs.shape[-1]

    def _image_embed(self, image_urls, images_base64):
        model, processor = get_clip_model()
        images = self._load_images(image_urls, images_base64)
        inputs = processor(images=images, return_tensors="pt")
        outputs = model.get_image_features(**inputs)
        vecs = _embedding_tensor(outputs).detach().cpu().numpy()
        return vecs.tolist(), vecs.shape[-1]

    def _similarity(self, text: str, image_urls, images_base64):
        model, processor = get_clip_model()
        images = self._load_images(image_urls, images_base64)
        inputs = processor(text=[text], images=images, return_tensors="pt", padding=True)
        outputs = model(**inputs)
        # logits_per_image shape: [N_images, 1]; softmax dim=1 → per-image score
        scores = torch.nn.functional.softmax(outputs.logits_per_image, dim=1).detach().cpu().numpy()
        return scores.flatten().tolist()

    async def text_embedding(self, req: TextEmbeddingRequest) -> ClipEmbeddingResponse:
        import os

        model_name = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
        loop = asyncio.get_event_loop()
        vecs, dims = await loop.run_in_executor(_executor.get(), self._text_embed, req.texts)
        return ClipEmbeddingResponse(model=model_name, dimensions=dims, embeddings=vecs)

    async def image_embedding(self, req: ImageEmbeddingRequest) -> ClipEmbeddingResponse:
        import os

        model_name = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
        loop = asyncio.get_event_loop()
        vecs, dims = await loop.run_in_executor(
            _executor.get(), self._image_embed, req.image_urls, req.images_base64
        )
        return ClipEmbeddingResponse(model=model_name, dimensions=dims, embeddings=vecs)

    async def similarity(self, req: SimilarityRequest) -> SimilarityResponse:
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            _executor.get(), self._similarity, req.text, req.image_urls, req.images_base64
        )
        return SimilarityResponse(text=req.text, scores=scores)


def close() -> None:
    _executor.close()
