"""Video service — DDGS video search."""

import asyncio
import time
import logging

from app.models import VideoSearchRequest, VideoSearchResponse, VideoResultItem

logger = logging.getLogger("videos")


class VideoService:
    """Search videos via DDGS."""

    async def search(self, req: VideoSearchRequest) -> VideoSearchResponse:
        timings: dict[str, float] = {}

        # ── Step 1: DDGS Video Search ───────────────────────────────────
        t0 = time.time()
        try:
            raw = await self._search_ddgs(req)
        except Exception as e:
            logger.error("DDGS video search failed: %s", e)
            return VideoSearchResponse(
                query=req.query, number_of_results=0, results=[], timings=timings,
            )

        timings["search"] = round(time.time() - t0, 2)

        # ── Step 2: Build results ──────────────────────────────────────
        results = []
        for item in raw:
            results.append(VideoResultItem(
                title=item.get("title", ""),
                url=item.get("content", ""),
                publisher=item.get("publisher"),
                duration=item.get("duration"),
                views=item.get("views"),
                thumbnail_url=item.get("thumbnail"),
                published=item.get("published"),
                description=item.get("description"),
                engine="ddgs",
            ))

        timings["total"] = round(sum(timings.values()), 2)

        return VideoSearchResponse(
            query=req.query,
            number_of_results=len(results),
            results=results,
            timings=timings,
        )

    async def _search_ddgs(self, req: VideoSearchRequest) -> list[dict]:
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None,
            self._ddgs_videos,
            req.query,
            req.max_results,
            req.region,
            req.safesearch,
            req.timelimit,
            req.resolution,
            req.duration,
            req.license_video,
        )
        return raw

    def _ddgs_videos(self, query: str, max_results: int, region: str,
                     safesearch: str, timelimit: str | None,
                     resolution: str | None, duration: str | None,
                     license_video: str | None) -> list[dict]:
        from ddgs import DDGS

        kwargs = {
            "query": query,
            "region": region,
            "safesearch": safesearch,
            "max_results": max_results,
        }
        if timelimit:
            kwargs["timelimit"] = timelimit
        if resolution:
            kwargs["resolution"] = resolution
        if duration:
            kwargs["duration"] = duration
        if license_video:
            kwargs["license_video"] = license_video

        with DDGS() as ddgs:
            return list(ddgs.videos(**kwargs))


video_service = VideoService()
