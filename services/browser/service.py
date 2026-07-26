import base64
import logging

from models import BrowseRequest, BrowseResponse

logger = logging.getLogger("browser")


class BrowserService:
    """
    Wraps Camoufox (a stealth Firefox build) via Playwright's async API.
    Camoufox exposes a Playwright-compatible server; we connect via CDP/websocket
    using the CAMOUFOX_WS_ENDPOINT, falling back to a local Playwright browser
    for local/dev usage.
    """

    async def browse(self, req: BrowseRequest) -> BrowseResponse:
        from playwright.async_api import async_playwright
        import os

        ws_endpoint = os.getenv("CAMOUFOX_WS_ENDPOINT")

        async with async_playwright() as p:
            if ws_endpoint:
                browser = await p.firefox.connect(ws_endpoint)
            else:
                browser = await p.firefox.launch(headless=True)

            page = await browser.new_page()
            try:
                await page.goto(str(req.url), wait_until="networkidle", timeout=30000)
                if req.wait_ms:
                    await page.wait_for_timeout(req.wait_ms)

                if req.action == "screenshot":
                    img_bytes = await page.screenshot(full_page=req.full_page)
                    return BrowseResponse(
                        url=str(req.url),
                        action=req.action,
                        screenshot_base64=base64.b64encode(img_bytes).decode(),
                    )
                elif req.action == "content":
                    content = await page.content()
                    return BrowseResponse(url=str(req.url), action=req.action, content=content)
                elif req.action == "click":
                    if not req.selector:
                        return BrowseResponse(
                            url=str(req.url), action=req.action, success=False,
                            message="selector is required for click action",
                        )
                    await page.click(req.selector, timeout=10000)
                    content = await page.content()
                    return BrowseResponse(url=str(req.url), action=req.action, content=content)
                elif req.action == "fill_form":
                    if not req.selector or req.text is None:
                        return BrowseResponse(
                            url=str(req.url), action=req.action, success=False,
                            message="selector and text are required for fill_form action",
                        )
                    await page.fill(req.selector, req.text)
                    content = await page.content()
                    return BrowseResponse(url=str(req.url), action=req.action, content=content)
            finally:
                await browser.close()


browser_service = BrowserService()
