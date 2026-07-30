"""Security middleware stack for FastAPI.

Layers (applied in order):
  1. CORS — configurable origin restrictions
  2. Request size limit — reject oversized payloads
  3. Auth dependency — JWT or API key on protected endpoints
  4. Rate limiting — Redis-backed per-IP or per-key sliding window
  5. Security headers — HSTS, nosniff, etc.
"""

import os
import logging
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import (
    PUBLIC_PATHS,
    RATE_LIMIT_ANON,
    RATE_LIMIT_AUTH,
    decode_jwt,
    validate_api_key,
    check_rate_limit,
    get_client_ip,
)

logger = logging.getLogger("middleware")

# Configuration
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", str(10 * 1024 * 1024)))  # 10 MB default
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")  # comma-separated or *
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"


# ── Request Size Limiter ──────────────────────────────────────────────────

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies larger than MAX_BODY_BYTES."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large (max {MAX_BODY_BYTES} bytes)"},
            )
        return await call_next(request)


# ── Security Headers ───────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Request-ID"] = request.headers.get("x-request-id", "")
        return response


# ── Auth + Rate Limiting Middleware ─────────────────────────────────────────

class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Combined authentication and rate limiting.

    Auth method (in order of precedence):
      1. Bearer JWT token in Authorization header
      2. X-API-Key header
      3. Anonymous (rate-limited)

    Public paths skip authentication but are still rate-limited.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = get_client_ip(request)

        # Skip auth for public endpoints
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            allowed, remaining, resets_at = await check_rate_limit(f"anon:{client_ip}", RATE_LIMIT_ANON)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "retry_after": 60},
                    headers={"Retry-After": "60", "X-RateLimit-Limit": str(RATE_LIMIT_ANON), "X-RateLimit-Remaining": "0"},
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_ANON)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        # If auth is disabled, skip authentication
        if not AUTH_ENABLED:
            return await call_next(request)

        # ── Authenticate ──────────────────────────────────────────────────
        auth_identifier = None
        auth_limit = RATE_LIMIT_ANON

        # Try JWT
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_jwt(token)
            if payload:
                auth_identifier = f"jwt:{payload.get('sub', 'unknown')}"
                auth_limit = RATE_LIMIT_AUTH
            else:
                return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        # Try API key
        if not auth_identifier:
            api_key = request.headers.get("x-api-key", "")
            if api_key:
                key_info = await validate_api_key(api_key)
                if key_info:
                    name = key_info.get("name", "unknown")
                    auth_identifier = f"apikey:{name}"
                    custom_limit = key_info.get("rate_limit")
                    auth_limit = int(custom_limit) if custom_limit else RATE_LIMIT_AUTH
                else:
                    return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        # Anonymous
        if not auth_identifier:
            auth_identifier = f"anon:{client_ip}"
            auth_limit = RATE_LIMIT_ANON

        # ── Rate limit ────────────────────────────────────────────────────
        allowed, remaining, resets_at = await check_rate_limit(auth_identifier, auth_limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": 60},
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(auth_limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # ── Process request ───────────────────────────────────────────────
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(auth_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-Auth-Method"] = "jwt" if auth_identifier.startswith("jwt:") else "apikey" if auth_identifier.startswith("apikey:") else "anonymous"
        return response


# ── Setup function ─────────────────────────────────────────────────────────

def setup_security(app: FastAPI):
    """Install all security middleware on the FastAPI app.

    Execution order (last added = first executed on request):
      1. Security headers  (outermost — adds headers to response)
      2. Auth + rate limit  (authenticates + rate-limits)
      3. Request size limit (rejects oversized payloads)
      4. CORS              (innermost — handles preflight)
    """
    # Add in REVERSE execution order (last added = first executed)
    # 1. Security headers (outermost — always runs)
    app.add_middleware(SecurityHeadersMiddleware)
    # 2. Auth + Rate limiting
    app.add_middleware(AuthRateLimitMiddleware)
    # 3. Request size limit
    app.add_middleware(RequestSizeLimitMiddleware)
    # 4. CORS (innermost — handles preflight before auth)
    origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
    if origins and origins != ["*"]:
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
