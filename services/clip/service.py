import os
import io
import base64
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

import httpx

from models import (
    TextEmbeddingRequest, ImageEmbeddingRequest, EmbeddingResponse,
    SimilarityRequest, SimilarityResponse,
)

logger = logging.getLogger("clip")

MODEL_NAME = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
_executor = ThreadPoolExecutor(max_workers=2)


class ClipService:
    def __init__(self):
        self._model = None
        self._processor = None

    def _load(self):
        if self._model is None:
            from transformers import CLIPModel, CLIPProcessor
            logger.info("Loading CLIP model %s", MODEL_NAME)
            self._model = CLIPModel.from_pretrained(MODEL_NAME, cache_dir=os.getenv("HF_HOME"))
            self._processor = CLIPProcessor.from_pretrained(MODEL_NAME, cache_dir=os.getenv("HF_HOME"))
        return self._model, self._processor

    def _load_images(self, image_urls, images_base64):
        from PIL import Image
        images = []
        if image_urls:
            for url in image_urls:
                resp = httpx.get(url, timeout=20.0)
                resp.raise_for_status()
                images.append(Image.open(io.BytesIO(resp.content)).convert("RGB"))
        if images_base64:
            for b64 in images_base64:
                images.append(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"))
        return images

    def _text_embed(self, texts: list[str]):
        model, processor = self._load()
        inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True)
        outputs = model.get_text_features(**inputs)
        vecs = outputs.detach().cpu().numpy()
        return vecs.tolist(), vecs.shape[-1]

    def _image_embed(self, image_urls, images_base64):
        model, processor = self._load()
        images = self._load_images(image_urls, images_base64)
        inputs = processor(images=images, return_tensors="pt")
        outputs = model.get_image_features(**inputs)
        vecs = outputs.detach().cpu().numpy()
        return vecs.tolist(), vecs.shape[-1]

    def _similarity(self, text: str, image_urls, images_base64):
        import torch
        model, processor = self._load()
        images = self._load_images(image_urls, images_base64)
        inputs = processor(text=[text], images=images, return_tensors="pt", padding=True)
        outputs = model(**inputs)
        logits_per_image = outputs.logits_per_image
        scores = torch.nn.functional.softmax(logits_per_image, dim=0).squeeze(-1).detach().cpu().numpy()
        return scores.tolist()

    async def text_embedding(self, req: TextEmbeddingRequest) -> EmbeddingResponse:
        loop = asyncio.get_event_loop()
        vecs, dims = await loop.run_in_executor(_executor, self._text_embed, req.texts)
        return EmbeddingResponse(model=MODEL_NAME, dimensions=dims, embeddings=vecs)

    async def image_embedding(self, req: ImageEmbeddingRequest) -> EmbeddingResponse:
        loop = asyncio.get_event_loop()
        vecs, dims = await loop.run_in_executor(
            _executor, self._image_embed, req.image_urls, req.images_base64
        )
        return EmbeddingResponse(model=MODEL_NAME, dimensions=dims, embeddings=vecs)

    async def similarity(self, req: SimilarityRequest) -> SimilarityResponse:
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            _executor, self._similarity, req.text, req.image_urls, req.images_base64
        )
        return SimilarityResponse(text=req.text, scores=scores)


clip_service = ClipService()
