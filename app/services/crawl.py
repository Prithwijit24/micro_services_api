"""Validated web crawling with a static fetch and browser fallback."""

from __future__ import annotations

import asyncio
import logging
import re
from app.services.executors import ManagedExecutor

from app.models import BrowseRequest, CrawlRequest, CrawlResponse
from app.services.browse import BrowserService
from app.services.url_policy import UnsafeURL, safe_http_get, validate_public_url

logger = logging.getLogger("crawl")
_executor = ManagedExecutor(4, "crawl")


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_markdown(html: str, only_main_content: bool) -> str:
    import trafilatura

    return (
        trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            output_format="markdown",
            favor_recall=only_main_content,
        )
        or ""
    ).strip()


class CrawlService:
    """Fetch public web pages and escalate thin pages to a guarded browser."""

    async def crawl(self, req: CrawlRequest) -> CrawlResponse:
        await validate_public_url(str(req.url))
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(_executor.get(), self._crawl_static, req),
                timeout=req.timeout_ms / 1000,
            )
        except UnsafeURL:
            raise
        except Exception as exc:
            logger.warning("Static crawl failed for %s: %s", req.url, exc)
            result = CrawlResponse(url=str(req.url), markdown="")

        if result.markdown and len(result.markdown) >= 50:
            return result

        try:
            browser_result = await asyncio.wait_for(
                BrowserService().browse(
                    BrowseRequest(url=req.url, action="content", wait_ms=1000)
                ),
                timeout=req.timeout_ms / 1000,
            )
            if browser_result.content:
                markdown = await asyncio.to_thread(
                    _extract_markdown, browser_result.content, req.only_main_content
                )
                if markdown:
                    return CrawlResponse(
                        url=str(req.url),
                        markdown=markdown,
                        html=browser_result.content if req.include_html else None,
                        title=_extract_title(browser_result.content) or None,
                        status_code=200,
                    )
        except Exception as exc:
            logger.warning("Browser crawl fallback failed for %s: %s", req.url, exc)

        return result

    def _crawl_static(self, req: CrawlRequest) -> CrawlResponse:
        response = safe_http_get(
            str(req.url),
            timeout=req.timeout_ms / 1000,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-Infra-Stack/2.1)"},
        )
        response.raise_for_status()
        html = response.text
        return CrawlResponse(
            url=str(response.url),
            markdown=_extract_markdown(html, req.only_main_content),
            html=html if req.include_html else None,
            title=_extract_title(html) or None,
            status_code=response.status_code,
        )


crawl_service = CrawlService()


def close() -> None:
    _executor.close()
