"""Free proxy manager — fetches, validates, and rotates free proxies for anti-detection.

Uses the `free-proxy` library to fetch public proxy lists and validates them
against target sites. Proxies are cached and rotated to avoid detection.

Design goals:
- Non-blocking: get_proxy() never blocks the caller. If no proxy is cached,
  returns None immediately and refreshes in the background.
- Fast fallback: If proxy acquisition fails, callers fall back to direct connection.
- Background refresh: Proxy pool is refreshed in a background thread on startup
  and periodically.

Usage:
    proxy_manager = ProxyManager()
    proxy = proxy_manager.get_proxy()  # Returns a validated proxy URL or None
"""

import os
import time
import random
import logging
import threading
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("proxy")

# Configuration
PROXY_VALIDATE_TIMEOUT = int(os.getenv("PROXY_VALIDATE_TIMEOUT", "3"))
PROXY_CACHE_TTL = int(os.getenv("PROXY_CACHE_TTL", "300"))  # 5 minutes
PROXY_MIN_POOL_SIZE = int(os.getenv("PROXY_MIN_POOL_SIZE", "3"))
PROXY_FETCH_TIMEOUT = int(os.getenv("PROXY_FETCH_TIMEOUT", "15"))  # Max seconds to spend fetching proxies

_executor = ThreadPoolExecutor(max_workers=1)


class ProxyManager:
    """Manages free proxy pool with validation and rotation.

    Thread-safe. All proxy fetching happens in background threads.
    get_proxy() is non-blocking — returns None if no proxy is available yet.
    """

    def __init__(self):
        self._pool: list[str] = []
        self._lock = threading.Lock()
        self._last_refresh: float = 0
        self._refreshing = False

    def get_proxy(self) -> Optional[str]:
        """Get a validated proxy URL. Non-blocking — returns None if pool is empty."""
        with self._lock:
            pool = list(self._pool)
            last = self._last_refresh

        # Check if refresh is needed
        needs_refresh = (
            len(pool) < PROXY_MIN_POOL_SIZE
            or (time.time() - last) > PROXY_CACHE_TTL
        )

        if needs_refresh and not self._refreshing:
            self._trigger_background_refresh()

        if pool:
            return random.choice(pool)
        return None

    def get_proxy_dict(self) -> Optional[dict]:
        """Get proxy dict for httpx/requests."""
        proxy = self.get_proxy()
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}

    def _trigger_background_refresh(self):
        """Trigger a background proxy pool refresh."""
        self._refreshing = True

        def _do_refresh():
            try:
                proxies = self._fetch_proxies()
                with self._lock:
                    if proxies:
                        self._pool = proxies
                        self._last_refresh = time.time()
                        logger.info("Background proxy refresh: %d proxies", len(proxies))
                    else:
                        logger.warning("Background proxy refresh: no proxies found")
            except Exception as e:
                logger.error("Background proxy refresh failed: %s", e)
            finally:
                self._refreshing = False

        threading.Thread(target=_do_refresh, daemon=True).start()

    def _fetch_proxies(self) -> list[str]:
        """Fetch free proxies with a hard timeout. Runs in a thread."""
        try:
            from fp.fp import FreeProxy
        except ImportError:
            logger.warning("free-proxy not installed: pip install free-proxy")
            return []

        proxies = []
        start = time.time()

        for attempt in range(15):
            # Hard timeout
            if (time.time() - start) > PROXY_FETCH_TIMEOUT:
                logger.info("Proxy fetch timeout after %.1fs (%d proxies)", time.time() - start, len(proxies))
                break

            try:
                proxy = FreeProxy(
                    https=True,
                    elite=True,
                    timeout=PROXY_VALIDATE_TIMEOUT,
                    rand=True,
                ).get()
                if proxy and proxy.startswith("http"):
                    proxies.append(proxy)
            except Exception:
                continue

            if len(proxies) >= PROXY_MIN_POOL_SIZE:
                break

        # Deduplicate
        return list(set(proxies))


class UserAgentRotator:
    """Rotates user agents to avoid fingerprinting."""

    DESKTOP_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    ]

    @classmethod
    def get_random_ua(cls) -> str:
        return random.choice(cls.DESKTOP_UAS)

    @classmethod
    def get_chrome_ua(cls) -> str:
        return next(
            (ua for ua in cls.DESKTOP_UAS if "Chrome" in ua and "Edg" not in ua),
            cls.DESKTOP_UAS[0],
        )

    @classmethod
    def get_firefox_ua(cls) -> str:
        return next(
            (ua for ua in cls.DESKTOP_UAS if "Firefox" in ua),
            cls.DESKTOP_UAS[3],
        )


# Singleton instances
proxy_manager = ProxyManager()
ua_rotator = UserAgentRotator()
