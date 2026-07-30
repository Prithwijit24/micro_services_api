"""Crawl service — static fetcher with stealthy fallback chain for JS-heavy sites.

Proxy routing: All HTTP requests are routed through rotating free proxies
to avoid IP-based detection on cloud VMs.
"""

import os
import re
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.models import CrawlRequest, CrawlResponse
from app.services.proxy import proxy_manager, ua_rotator

logger = logging.getLogger("crawl")
CRAWL_ENGINE = os.getenv("CRAWL_ENGINE", "trafilatura")
USE_PROXIES = os.getenv("USE_PROXIES", "false").lower() == "true"

_executor = ThreadPoolExecutor(max_workers=4)


def _html_to_markdown(html: str) -> str:
    """Convert HTML to Markdown using html2text."""
    import html2text

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    return h.handle(html).strip()


def _extract_title(html: str) -> str:
    """Extract <title> from raw HTML."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


class CrawlService:
    """Extracts clean markdown from URLs.

    Fallback chain:
      1. Static fetch (Trafilatura / Scrapling Fetcher)
      2. Scrapling StealthyFetcher (stealthy browser, no Playwright fingerprints)
      3. Playwright browser (full rendering)
    """

    async def crawl(self, req: CrawlRequest) -> CrawlResponse:
        loop = asyncio.get_running_loop()
        timeout_s = req.timeout_ms / 1000

        # Layer 1: Static fetch — try primary first, fall back to secondary
        fetchers = [self._crawl_scrapling, self._crawl_trafilatura] if CRAWL_ENGINE == "scrapling" else [self._crawl_trafilatura, self._crawl_scrapling]
        result = CrawlResponse(url=str(req.url), markdown="", status_code=None, title=None)
        best = result
        for fetcher in fetchers:
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(_executor, fetcher, req),
                    timeout=timeout_s,
                )
                if len(result.markdown or "") > len(best.markdown or ""):
                    best = result
                if result.markdown and len(result.markdown) >= 50:
                    break
                logger.info("Static fetch via %s thin for %s (%d chars), trying next",
                            fetcher.__name__, req.url, len(result.markdown or ""))
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning("Static fetch %s failed for %s: %s", fetcher.__name__, req.url, e)
        result = best

        # If content is short (bot challenge / JS-rendered), escalate
        if not result.markdown or len(result.markdown) < 50:
            logger.info("Static crawl thin for %s (%d chars), trying StealthyFetcher",
                        req.url, len(result.markdown or ""))

            # Layer 2: Scrapling StealthyFetcher (stealthy browser without Playwright fingerprints)
            result = await self._crawl_via_stealthy_fetcher(req, result)

        # Layer 3: Full Playwright browser
        if not result.markdown or len(result.markdown) < 50:
            logger.info("StealthyFetcher thin for %s (%d chars), trying Playwright browser",
                        req.url, len(result.markdown or ""))
            result = await self._crawl_via_browser(req, result)

        return result

    async def _crawl_via_stealthy_fetcher(self, req: CrawlRequest, failed: CrawlResponse) -> CrawlResponse:
        """Layer 2: Use Scrapling StealthyFetcher — stealthy browser with anti-detection."""
        import trafilatura

        try:
            from scrapling.fetchers import StealthyFetcher

            def _fetch():
                return StealthyFetcher.fetch(
                    str(req.url),
                    block_images=True,
                    timeout=30000,
                )

            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(_executor, _fetch)

            html = resp.text if hasattr(resp, "text") else ""
            if not html or len(html) < 50:
                return failed

            markdown = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                output_format="markdown",
                favor_recall=True,
            ) or _html_to_markdown(html)

            title = failed.title or _extract_title(html)

            return CrawlResponse(
                url=str(req.url),
                markdown=markdown,
                html=html if req.include_html else None,
                title=title or None,
                status_code=200,
            )
        except Exception as e:
            logger.warning("StealthyFetcher failed for %s: %s", req.url, e)
            return failed

    async def _crawl_via_browser(self, req: CrawlRequest, failed: CrawlResponse) -> CrawlResponse:
        """Layer 3: Use Playwright browser to render the page, then extract markdown."""
        import trafilatura

        try:
            from app.services.browse import BrowserService
            from app.models import BrowseRequest

            browser = BrowserService()
            page = await browser.browse(BrowseRequest(url=req.url, action="content", wait_ms=3000))

            if not page.content:
                return failed

            markdown = trafilatura.extract(
                page.content,
                include_comments=False,
                include_tables=True,
                output_format="markdown",
                favor_recall=True,
            ) or _html_to_markdown(page.content)

            title = failed.title or _extract_title(page.content)

            return CrawlResponse(
                url=str(req.url),
                markdown=markdown,
                html=page.content if req.include_html else None,
                title=title or None,
                status_code=200,
            )
        except Exception as e:
            logger.warning("browser fallback failed for %s: %s", req.url, e)
            return failed

    def _crawl_scrapling(self, req: CrawlRequest) -> CrawlResponse:
        """Use Scrapling Fetcher + html2text for content extraction.

        Routes through rotating free proxies when USE_PROXIES=true.
        """
        from scrapling import Fetcher

        proxy_url = proxy_manager.get_proxy() if USE_PROXIES else None
        user_agent = ua_rotator.get_random_ua()

        try:
            fetcher = Fetcher(auto_match=False)
            kwargs = {"timeout": req.timeout_ms / 1000}
            if proxy_url:
                kwargs["proxies"] = {"http": proxy_url, "https": proxy_url}
                logger.debug("Scrapling fetching %s via proxy %s", req.url, proxy_url)

            response = fetcher.get(str(req.url), **kwargs)

            html = response.text if hasattr(response, "text") else ""
            title = _extract_title(html)
            status_code = response.status_code if hasattr(response, "status_code") else None

            markdown = _html_to_markdown(html) if html else ""

            return CrawlResponse(
                url=str(req.url),
                markdown=markdown,
                html=html if req.include_html else None,
                title=title or None,
                status_code=status_code,
            )
        except Exception as e:
            logger.warning("Scrapling failed for %s: %s", req.url, e)
            return CrawlResponse(
                url=str(req.url),
                markdown="",
                status_code=None,
                title=None,
            )

    def _crawl_trafilatura(self, req: CrawlRequest) -> CrawlResponse:
        """Fetch via httpx (with timeout), extract via Trafilatura.

        Routes through rotating free proxies when USE_PROXIES=true.
        """
        import httpx
        import trafilatura
        from trafilatura.settings import use_config as trafilatura_config

        # Get proxy and rotate user agent
        proxy_url = proxy_manager.get_proxy() if USE_PROXIES else None
        user_agent = ua_rotator.get_random_ua()

        try:
            kwargs = {
                "url": str(req.url),
                "follow_redirects": True,
                "timeout": req.timeout_ms / 1000,
                "headers": {"User-Agent": user_agent},
            }
            if proxy_url:
                kwargs["proxy"] = proxy_url
                logger.debug("Fetching %s via proxy %s", req.url, proxy_url)

            resp = httpx.get(**kwargs)
            resp.raise_for_status()
            downloaded = resp.text
        except Exception:
            # Retry without proxy on failure
            if proxy_url:
                try:
                    logger.info("Proxy failed for %s, retrying direct", req.url)
                    resp = httpx.get(
                        str(req.url),
                        follow_redirects=True,
                        timeout=req.timeout_ms / 1000,
                        headers={"User-Agent": user_agent},
                    )
                    resp.raise_for_status()
                    downloaded = resp.text
                except Exception:
                    return CrawlResponse(
                        url=str(req.url),
                        markdown="",
                        status_code=None,
                        title=None,
                    )
            else:
                return CrawlResponse(
                    url=str(req.url),
                    markdown="",
                    status_code=None,
                    title=None,
                )

        config = trafilatura_config()

        markdown = trafilatura.extract(
            downloaded,
            config=config,
            include_comments=False,
            include_tables=True,
            output_format="markdown",
            favor_recall=req.only_main_content,
        ) or ""

        if not markdown:
            markdown = _html_to_markdown(downloaded)

        title = _extract_title(downloaded)

        return CrawlResponse(
            url=str(req.url),
            markdown=markdown,
            html=downloaded if req.include_html else None,
            title=title or None,
            status_code=200,
        )


crawl_service = CrawlService()
