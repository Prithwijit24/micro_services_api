"""Authentication, API keys, and rate limiting middleware.

Security layers:
  1. JWT tokens (for user sessions / programmatic access)
  2. API keys (for service-to-service / long-lived access)
  3. Redis-backed rate limiting (per-key or per-IP)

Endpoints:
  POST /auth/token        — generate JWT (requires admin credentials)
  POST /auth/apikey       — create a new API key
  DELETE /auth/apikey     — revoke an API key
  GET  /auth/apikeys      — list all active API keys
  GET  /auth/rate-status  — check current rate limit status
"""

import os
import time
import uuid
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.deps import get_redis

logger = logging.getLogger("auth")

# ── Configuration ──────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Generate one with: openssl rand -hex 32\n"
        "Add it to your .env file: JWT_SECRET=<generated-value>"
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# Admin credentials for bootstrapping (JWT generation)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "")
if not ADMIN_PASS:
    raise RuntimeError(
        "ADMIN_PASS is not set. Add it to your .env file: ADMIN_PASS=<strong-password>"
    )

# Rate limiting defaults (requests per second)
RATE_LIMIT_ANON = int(os.getenv("RATE_LIMIT_ANON", "20"))
RATE_LIMIT_AUTH = int(os.getenv("RATE_LIMIT_AUTH", "300"))

# Trusted proxy header (set if behind Caddy/nginx)
TRUSTED_PROXY = os.getenv("TRUSTED_PROXY", "127.0.0.1")

# Endpoints that bypass authentication (health, docs, OpenAPI, auth itself)
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/token",
}


# ── Models ─────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until expiry")


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Human-readable label")
    rate_limit: Optional[int] = Field(default=None, description="Custom rate limit (req/sec). Null = default.")
    expires_days: Optional[int] = Field(default=None, description="Days until expiry. Null = never.")


class ApiKeyResponse(BaseModel):
    key: str
    name: str
    rate_limit: Optional[int] = None
    expires_at: Optional[str] = None
    created_at: str


class ApiKeyInfo(BaseModel):
    key_prefix: str
    name: str
    rate_limit: Optional[int] = None
    expires_at: Optional[str] = None
    created_at: str


class RateStatusResponse(BaseModel):
    identifier: str
    limit: int
    remaining: int
    resets_at: str


# ── JWT Helpers ────────────────────────────────────────────────────────────

def create_jwt(username: str, expires_hours: int = JWT_EXPIRY_HOURS) -> str:
    """Create a signed JWT token."""
    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[dict]:
    """Decode and verify a JWT token. Returns None if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ── API Key Helpers ────────────────────────────────────────────────────────

def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key: `aistack_` + 48-char hex."""
    return f"aistack_{uuid.uuid4().hex}{uuid.uuid4().hex[:16]}"


async def store_api_key(name: str, raw_key: str, rate_limit: Optional[int], expires_days: Optional[int]) -> dict:
    """Store an API key in Redis. Returns the key info dict."""
    client = get_redis()
    key_hash = _hash_key(raw_key)
    now = datetime.now(timezone.utc).isoformat()

    expires_at = None
    ttl_seconds = None
    if expires_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
        ttl_seconds = expires_days * 86400

    info = {
        "name": name,
        "key_prefix": raw_key[:16] + "...",
        "created_at": now,
    }
    if rate_limit is not None:
        info["rate_limit"] = rate_limit
    if expires_at is not None:
        info["expires_at"] = expires_at

    pipe = client.pipeline()
    pipe.hset(f"apikey:{key_hash}", mapping={k: str(v) for k, v in info.items()})
    pipe.sadd("apikeys", key_hash)
    if ttl_seconds:
        pipe.expire(f"apikey:{key_hash}", ttl_seconds)
        pipe.expire("apikeys", ttl_seconds)
    await pipe.execute()

    return {**info, "key": raw_key}


async def validate_api_key(raw_key: str) -> Optional[dict]:
    """Validate an API key. Returns key info dict if valid, None otherwise."""
    client = get_redis()
    key_hash = _hash_key(raw_key)
    info = await client.hgetall(f"apikey:{key_hash}")
    if not info:
        return None

    # Sanitize "None" strings (legacy storage bug fix)
    for k, v in info.items():
        if v == "None":
            info[k] = None

    # Check expiry
    expires_at = info.get("expires_at")
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at)
            if datetime.now(timezone.utc) > exp_dt:
                await revoke_api_key(raw_key)
                return None
        except ValueError:
            pass

    return info


async def revoke_api_key(raw_key: str) -> bool:
    """Revoke an API key."""
    client = get_redis()
    key_hash = _hash_key(raw_key)
    pipe = client.pipeline()
    pipe.delete(f"apikey:{key_hash}")
    pipe.srem("apikeys", key_hash)
    results = await pipe.execute()
    return results[0] > 0


async def list_api_keys() -> list[dict]:
    """List all active API keys (returns info only, not the raw keys)."""
    client = get_redis()
    key_hashes = await client.smembers("apikeys")
    keys = []
    for h in key_hashes:
        info = await client.hgetall(f"apikey:{h}")
        if info:
            # Convert "None" strings back to actual None (legacy data fix)
            cleaned = {}
            for k, v in info.items():
                cleaned[k] = None if v == "None" else v
            keys.append(cleaned)
    return keys


# ── Rate Limiting ──────────────────────────────────────────────────────────

async def check_rate_limit(identifier: str, limit: int) -> tuple[bool, int, int]:
    """Check rate limit using sliding window counter in Redis.

    Window is 1 second (rate limits are expressed in requests-per-second).
    Returns: (allowed, remaining, resets_at_unix)
    """
    client = get_redis()
    now = time.time()
    window = 1  # 1-second sliding window (req/sec semantics)
    window_start = now - window

    key = f"ratelimit:{identifier}"
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)  # Remove old entries
    pipe.zadd(key, {str(uuid.uuid4()): now})     # Add current request
    pipe.zcard(key)                                # Count requests in window
    pipe.expire(key, window + 10)                  # Auto-cleanup
    results = await pipe.execute()

    request_count = results[2]
    remaining = max(0, limit - request_count)
    resets_at = int(now + window)

    allowed = request_count <= limit
    return allowed, remaining, resets_at


def get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind reverse proxy."""
    if TRUSTED_PROXY:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        xri = request.headers.get("x-real-ip")
        if xri:
            return xri.strip()
    return request.client.host if request.client else "unknown"


# ── Router ─────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(req: TokenRequest):
    """Generate a JWT token. Requires admin credentials."""
    if req.username != ADMIN_USER or req.password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(req.username)
    return TokenResponse(access_token=token, expires_in=JWT_EXPIRY_HOURS * 3600)


@router.post("/apikey", response_model=ApiKeyResponse)
async def create_api_key(req: ApiKeyCreateRequest, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Create a new API key. Requires valid JWT."""
    payload = decode_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    raw_key = generate_api_key()
    info = await store_api_key(req.name, raw_key, req.rate_limit, req.expires_days)
    return ApiKeyResponse(**info)


@router.delete("/apikey")
async def delete_api_key(key: str, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Revoke an API key."""
    payload = decode_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    revoked = await revoke_api_key(key)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"deleted": True}


@router.get("/apikeys", response_model=list[ApiKeyInfo])
async def list_keys(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """List all active API keys."""
    payload = decode_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    keys = await list_api_keys()
    return [ApiKeyInfo(**k) for k in keys]


@router.get("/rate-status", response_model=RateStatusResponse)
async def rate_status(request: Request, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Check current rate limit status."""
    payload = decode_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    client_ip = get_client_ip(request)
    allowed, remaining, resets_at = await check_rate_limit(f"ip:{client_ip}", RATE_LIMIT_AUTH)
    return RateStatusResponse(
        identifier=client_ip,
        limit=RATE_LIMIT_AUTH,
        remaining=remaining,
        resets_at=datetime.fromtimestamp(resets_at, tz=timezone.utc).isoformat(),
    )
