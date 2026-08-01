"""Image service — DDGS → Unsplash → Pexels fallback chain, with CLIP reranking."""

import os
import asyncio
import time
import logging

from app.deps import get_http_client
from app.models import ImageSearchRequest, ImageSearchResponse, ImageResultItem, SimilarityRequest
from app.services.clip import ClipService

logger = logging.getLogger("images")

# DDGS extract timeout for news crawl (seconds)
DDGS_EXTRACT_TIMEOUT = 10.0

# ── Env vars for fallback providers ─────────────────────────────────────
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")


class ImageService:
    """Search images with fallback chain: DDGS → Unsplash → Pexels, CLIP rerank."""

    async def search(self, req: ImageSearchRequest) -> ImageSearchResponse:
        timings: dict[str, float] = {}

        # ── Step 1: Fetch images via fallback chain ─────────────────────
        t0 = time.time()
        try:
            raw, engine = await self._fetch_ddgs(req)
        except Exception as e:
            logger.warning("DDGS images failed: %s, trying Unsplash", e)
            try:
                raw, engine = await self._fetch_unsplash(req)
            except Exception as e2:
                logger.warning("Unsplash failed: %s, trying Pexels", e2)
                try:
                    raw, engine = await self._fetch_pexels(req)
                except Exception as e3:
                    logger.error("All image sources failed: DDGS=%s, Unsplash=%s, Pexels=%s", e, e2, e3)
                    return ImageSearchResponse(
                        query=req.query, number_of_results=0, results=[],
                        timings=timings, clip_enabled=False,
                    )

        timings["search"] = round(time.time() - t0, 2)

        if not raw:
            return ImageSearchResponse(
                query=req.query, number_of_results=0, results=[],
                timings=timings, clip_enabled=False,
            )

        # ── Step 2: CLIP reranking ──────────────────────────────────────
        clip_enabled = False
        if req.use_clip:
            t1 = time.time()
            try:
                raw = await self._clip_rerank(req.query, raw, engine)
                clip_enabled = True
            except Exception as e:
                logger.warning("CLIP rerank failed, returning unranked results: %s", e)
            timings["clip"] = round(time.time() - t1, 2)

        # ── Step 3: Build result items ──────────────────────────────────
        results = []
        for item in raw:
            results.append(ImageResultItem(
                title=item.get("title", ""),
                image_url=item.get("image", ""),
                thumbnail_url=item.get("thumbnail"),
                source_url=item.get("url") or item.get("source_url"),
                width=item.get("width"),
                height=item.get("height"),
                clip_score=item.get("clip_score"),
                engine=engine,
            ))

        timings["total"] = round(sum(timings.values()), 2)

        return ImageSearchResponse(
            query=req.query,
            number_of_results=len(results),
            results=results,
            timings=timings,
            clip_enabled=clip_enabled,
        )

    # ── DDGS Images ────────────────────────────────────────────────────────

    async def _fetch_ddgs(self, req: ImageSearchRequest) -> tuple[list[dict], str]:
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None,
            self._ddgs_images,
            req.query,
            req.max_results,
            req.region,
            req.safesearch,
            req.size,
            req.color,
            req.type_image,
            req.layout,
            req.license_image,
        )
        if not raw:
            raise RuntimeError("DDGS returned no results")
        return raw, "ddgs"

    def _ddgs_images(self, query: str, max_results: int, region: str,
                     safesearch: str, size: str | None, color: str | None,
                     type_image: str | None, layout: str | None,
                     license_image: str | None) -> list[dict]:
        from ddgs import DDGS

        kwargs = {
            "query": query,
            "region": region,
            "safesearch": safesearch,
            "max_results": max_results,
        }
        if size:
            kwargs["size"] = size
        if color:
            kwargs["color"] = color
        if type_image:
            kwargs["type_image"] = type_image
        if layout:
            kwargs["layout"] = layout
        if license_image:
            kwargs["license_image"] = license_image

        with DDGS() as ddgs:
            return list(ddgs.images(**kwargs))

    # ── Unsplash ───────────────────────────────────────────────────────────

    async def _fetch_unsplash(self, req: ImageSearchRequest) -> tuple[list[dict], str]:
        if not UNSPLASH_ACCESS_KEY:
            raise RuntimeError("UNSPLASH_ACCESS_KEY not configured")

        client = get_http_client()
        resp = await client.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": req.query,
                "per_page": req.max_results,
            },
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            raise RuntimeError("Unsplash returned no results")

        normalized = []
        for item in results:
            urls = item.get("urls", {})
            normalized.append({
                "title": item.get("alt_description") or item.get("description") or "",
                "image": urls.get("regular", ""),
                "thumbnail": urls.get("small", ""),
                "source_url": item.get("links", {}).get("html", ""),
                "width": item.get("width"),
                "height": item.get("height"),
            })
        return normalized, "unsplash"

    # ── Pexels ─────────────────────────────────────────────────────────────

    async def _fetch_pexels(self, req: ImageSearchRequest) -> tuple[list[dict], str]:
        if not PEXELS_API_KEY:
            raise RuntimeError("PEXELS_API_KEY not configured")

        client = get_http_client()
        resp = await client.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": req.query,
                "per_page": req.max_results,
            },
            headers={"Authorization": PEXELS_API_KEY},
        )
        resp.raise_for_status()
        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            raise RuntimeError("Pexels returned no results")

        normalized = []
        for item in photos:
            src = item.get("src", {})
            normalized.append({
                "title": item.get("alt") or "",
                "image": src.get("large", ""),
                "thumbnail": src.get("small", ""),
                "source_url": item.get("url", ""),
                "width": item.get("width"),
                "height": item.get("height"),
            })
        return normalized, "pexels"

    # ── CLIP Reranking ─────────────────────────────────────────────────────

    async def _clip_rerank(self, query: str, items: list[dict],
                           engine: str) -> list[dict]:
        """Run CLIP similarity between query text and images, sort by score."""
        clip_svc = ClipService()

        # Extract image URLs — all engines normalize to "image" key
        image_urls = [item.get("image", "") for item in items]

        # Filter out empty URLs
        valid_pairs = [(i, url) for i, url in enumerate(image_urls) if url]
        if not valid_pairs:
            return items

        valid_indices = [p[0] for p in valid_pairs]
        valid_urls = [p[1] for p in valid_pairs]

        sim_req = SimilarityRequest(text=query, image_urls=valid_urls)
        sim_resp = await clip_svc.similarity(sim_req)

        # Attach scores to items (guard against partial download failures)
        n_scores = len(sim_resp.scores)
        for i, idx in enumerate(valid_indices):
            if i < n_scores:
                items[idx]["clip_score"] = round(sim_resp.scores[i], 4)

        # Sort by clip score descending (items without scores go to the end)
        items.sort(
            key=lambda x: x.get("clip_score", -1.0),
            reverse=True,
        )

        return items


image_service = ImageService()
