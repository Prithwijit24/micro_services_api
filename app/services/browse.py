"""Browser automation — Obscura cloud, local Playwright (Firefox primary), or StealthyFetcher.

The original code used Camoufox (stealthy Firefox) which bypasses bot detection on
sites like MakeMyTrip. Chromium is easily fingerprinted; Firefox has a different TLS
fingerprint, JS engine, and DOM API surface that anti-bot systems treat differently.

Proxy routing: All browser requests are routed through rotating free proxies
to avoid IP-based detection on cloud VMs.
"""

import os
import asyncio
import base64
import logging
from typing import Optional

from app.models import BrowseRequest, BrowseResponse
from app.services.proxy import proxy_manager, ua_rotator

logger = logging.getLogger("browse")

OBSCURA_CDP_URL = os.getenv("OBSCURA_CDP_URL", "")
USE_PROXIES = os.getenv("USE_PROXIES", "false").lower() == "true"


class BrowserService:
    async def browse(self, req: BrowseRequest) -> BrowseResponse:
        """Browse a URL with multi-layer fallback:
        1. Obscura cloud browser (if configured)
        2. Local Firefox (primary — bypasses bot detection like Camoufox)
        3. Local Chromium (fallback — different fingerprint)
        4. Scrapling StealthyFetcher (final fallback)
        """
        # Layer 1: Obscura cloud browser
        if OBSCURA_CDP_URL:
            try:
                return await self._browse_obscura(req)
            except Exception as e:
                logger.warning("Obscura browser failed for %s: %s", req.url, e)

        # Layer 2: Local Firefox (primary — best anti-detection)
        try:
            return await self._browse_local(req, browser_type="firefox")
        except Exception as e:
            logger.warning("Firefox failed for %s: %s", req.url, e)

        # Layer 3: Local Chromium with anti-detection
        try:
            return await self._browse_local(req, browser_type="chromium")
        except Exception as e:
            logger.warning("Chromium failed for %s: %s", req.url, e)

        # Layer 4: Scrapling StealthyFetcher
        try:
            return await self._browse_scrapling_stealth(req)
        except Exception as e:
            logger.warning("StealthyFetcher failed for %s: %s", req.url, e)

        return BrowseResponse(url=str(req.url), action=req.action, success=False,
                              message="All browser fallbacks failed")

    async def _browse_obscura(self, req: BrowseRequest) -> BrowseResponse:
        """Connect to Obscura cloud browser via CDP."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(OBSCURA_CDP_URL)
            logger.info("Connected to Obscura cloud browser")
            page = await browser.new_page()
            try:
                return await self._render_page(page, req)
            finally:
                await page.close()
                await browser.close()

    async def _browse_local(self, req: BrowseRequest, browser_type: str = "firefox") -> BrowseResponse:
        """Launch a local browser (firefox or chromium) with multiple wait strategies.

        Firefox has a different TLS/JS fingerprint than Chromium, which is why
        Camoufox (stealthy Firefox) bypasses bot detection on sites like MakeMyTrip.

        Routes through rotating free proxies when USE_PROXIES=true.
        """
        from playwright.async_api import async_playwright

        strategies = [
            {"wait_until": "domcontentloaded", "timeout": 25000},
            {"wait_until": "load", "timeout": 25000},
            {"wait_until": "networkidle", "timeout": 30000},
        ]

        # Chromium-specific anti-detection settings
        chromium_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-size=1920,1080",
        ]
        chromium_ua = ua_rotator.get_chrome_ua()
        chromium_init_script = """
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = { runtime: {} };
        """

        # Get a proxy for this browser session
        proxy_url = proxy_manager.get_proxy() if USE_PROXIES else None
        proxy_config = {"server": proxy_url} if proxy_url else None
        if proxy_config:
            logger.info("Using proxy %s for %s", proxy_url, browser_type)

        async with async_playwright() as p:
            if browser_type == "firefox":
                launch_kwargs = {"headless": True}
                if proxy_config:
                    launch_kwargs["proxy"] = proxy_config
                browser = await p.firefox.launch(**launch_kwargs)
            else:
                launch_kwargs = {"headless": True, "args": chromium_args}
                if proxy_config:
                    launch_kwargs["proxy"] = proxy_config
                browser = await p.chromium.launch(**launch_kwargs)

            try:
                for strat in strategies:
                    page = await browser.new_page(
                        user_agent=chromium_ua if browser_type == "chromium" else None
                    )
                    try:
                        if browser_type == "chromium":
                            await page.add_init_script(chromium_init_script)

                        await page.goto(str(req.url), wait_until=strat["wait_until"],
                                        timeout=strat["timeout"])
                        if req.wait_ms:
                            await page.wait_for_timeout(req.wait_ms)

                        result = await self._render_page(page, req)
                        if result.content and len(result.content) > 100:
                            logger.info("%s success with %s", browser_type.capitalize(),
                                        strat["wait_until"])
                            return result
                        logger.info("%s %s got thin content (%d chars), trying next",
                                    browser_type.capitalize(), strat["wait_until"],
                                    len(result.content or ""))
                    except Exception as e:
                        logger.info("%s %s failed: %s", browser_type.capitalize(),
                                    strat["wait_until"], e)
                    finally:
                        await page.close()
            finally:
                await browser.close()

        raise RuntimeError(f"All {browser_type} strategies exhausted")

    async def _browse_scrapling_stealth(self, req: BrowseRequest) -> BrowseResponse:
        """Use Scrapling StealthyFetcher — built-in anti-detection."""
        from scrapling.fetchers import StealthyFetcher

        def _fetch():
            return StealthyFetcher.fetch(str(req.url), block_images=True, timeout=30000)

        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, _fetch)

        html = resp.text if hasattr(resp, "text") else ""
        if not html:
            raise RuntimeError("StealthyFetcher returned empty content")

        return BrowseResponse(url=str(req.url), action=req.action, content=html)

    async def _render_page(self, page, req: BrowseRequest) -> BrowseResponse:
        """Extract content from a Playwright page based on action type."""
        if req.action == "screenshot":
            img_bytes = await page.screenshot(full_page=req.full_page)
            return BrowseResponse(
                url=str(req.url), action=req.action,
                screenshot_base64=base64.b64encode(img_bytes).decode(),
            )
        elif req.action == "content":
            content = await page.content()
            return BrowseResponse(url=str(req.url), action=req.action, content=content)
        elif req.action == "click":
            if not req.selector:
                return BrowseResponse(url=str(req.url), action=req.action, success=False,
                                      message="selector is required for click action")
            await page.click(req.selector, timeout=10000)
            content = await page.content()
            return BrowseResponse(url=str(req.url), action=req.action, content=content)
        elif req.action == "fill_form":
            if not req.selector or req.text is None:
                return BrowseResponse(url=str(req.url), action=req.action, success=False,
                                      message="selector and text are required for fill_form action")
            await page.fill(req.selector, req.text)
            content = await page.content()
            return BrowseResponse(url=str(req.url), action=req.action, content=content)
        return BrowseResponse(url=str(req.url), action=req.action, success=False,
                              message=f"Unknown action: {req.action}")
