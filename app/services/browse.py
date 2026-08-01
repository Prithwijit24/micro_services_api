"""Browser automation for public HTTP(S) pages."""

from __future__ import annotations

import asyncio
import base64
import logging

from app.models import BrowseRequest, BrowseResponse
from app.services.url_policy import UnsafeURL, validate_public_url

logger = logging.getLogger("browse")


class BrowserService:
    async def browse(self, req: BrowseRequest) -> BrowseResponse:
        """Render a validated public URL with Playwright."""
        await validate_public_url(str(req.url))
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (compatible; AI-Infra-Stack/2.1)"
                )

                async def guard(route, request):
                    try:
                        await validate_public_url(request.url)
                        await route.continue_()
                    except UnsafeURL:
                        await route.abort("blockedbyclient")

                await context.route("**/*", guard)
                page = await context.new_page()
                await page.goto(
                    str(req.url),
                    wait_until="domcontentloaded",
                    timeout=max(req.wait_ms + 15000, 15000),
                )
                if req.wait_ms:
                    await page.wait_for_timeout(req.wait_ms)
                return await self._render_page(page, req)
            finally:
                await browser.close()

    async def _render_page(self, page, req: BrowseRequest) -> BrowseResponse:
        if req.action == "screenshot":
            image = await page.screenshot(full_page=req.full_page)
            return BrowseResponse(
                url=str(req.url),
                action=req.action,
                screenshot_base64=base64.b64encode(image).decode(),
            )
        if req.action == "content":
            return BrowseResponse(
                url=str(req.url), action=req.action, content=await page.content()
            )
        if req.action == "click":
            if not req.selector:
                return BrowseResponse(
                    url=str(req.url), action=req.action, success=False,
                    message="selector is required for click action",
                )
            await page.click(req.selector, timeout=10000)
            return BrowseResponse(
                url=str(req.url), action=req.action, content=await page.content()
            )
        if req.action == "fill_form":
            if not req.selector or req.text is None:
                return BrowseResponse(
                    url=str(req.url), action=req.action, success=False,
                    message="selector and text are required for fill_form action",
                )
            await page.fill(req.selector, req.text)
            return BrowseResponse(
                url=str(req.url), action=req.action, content=await page.content()
            )
        return BrowseResponse(
            url=str(req.url), action=req.action, success=False,
            message=f"Unknown action: {req.action}",
        )
