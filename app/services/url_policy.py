"""Outbound URL policy for user-supplied HTTP(S) destinations."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import SplitResult, urljoin, urlsplit

import httpx


class UnsafeURL(ValueError):
    """Raised when a destination is not an allowed public HTTP(S) URL."""


def _parts(value: str) -> SplitResult:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURL("only http and https URLs are allowed")
    if not parsed.hostname:
        raise UnsafeURL("URL must include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeURL("URL credentials are not allowed")
    try:
        parsed.port
    except ValueError as exc:
        raise UnsafeURL("URL has an invalid port") from exc
    return parsed


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_public(value: str) -> str:
    parsed = _parts(value)
    host = parsed.hostname
    assert host is not None

    try:
        literal = ipaddress.ip_address(host)
        addresses = [str(literal)]
    except ValueError:
        try:
            addresses = sorted({
                result[4][0]
                for result in socket.getaddrinfo(
                    host,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            })
        except socket.gaierror as exc:
            raise UnsafeURL("hostname could not be resolved") from exc

    if not addresses or not all(_is_public(address) for address in addresses):
        raise UnsafeURL("private, local, or reserved destinations are not allowed")
    return value


def validate_public_url_sync(value: str) -> str:
    """Resolve and validate a URL in synchronous worker code."""
    return _resolve_public(str(value))


async def validate_public_url(value: str) -> str:
    """Resolve and validate a URL off the event loop before making a request."""
    return await asyncio.to_thread(validate_public_url_sync, str(value))


async def validate_public_urls(values: list[str] | None) -> None:
    """Validate a list of image or crawl destinations concurrently."""
    if values:
        await asyncio.gather(*(validate_public_url(value) for value in values))


def safe_http_get(
    value: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    max_redirects: int = 5,
) -> httpx.Response:
    """GET a public URL while revalidating every redirect destination."""
    current = validate_public_url_sync(value)
    request_headers = headers or {}

    with httpx.Client(follow_redirects=False, timeout=timeout) as client:
        for _ in range(max_redirects + 1):
            response = client.get(current, headers=request_headers)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            current = validate_public_url_sync(urljoin(current, location))

    raise UnsafeURL("too many redirects")
