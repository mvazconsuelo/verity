"""Everything that decides whether a request goes through, before it reaches ask(): origin, API
key, and rate limit. Closed by default: without keys, the gateway won't start.

ORIGIN_VERIFY_SECRET is optional and unset by default (nothing runs in front of the gateway in this
local-only setup) — verify_origin() below simply does nothing when it's empty. If a reverse proxy
or tunnel is ever put in front, set this to whatever secret header it injects.

API_KEYS is NOT stored in git: you export it yourself in your shell before bringing up the stack
(see app/run/run.sh).
"""
import hashlib
import os
import secrets
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]
AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"  # testing only
ORIGIN_VERIFY_SECRET = os.getenv("ORIGIN_VERIFY_SECRET", "")  # the header a reverse proxy would inject, if any
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))  # 0 = no limit
MAX_QUESTION_CHARS = int(os.getenv("MAX_QUESTION_CHARS", "2000"))

if not API_KEYS and not AUTH_DISABLED:
    raise RuntimeError("Set API_KEYS (export it yourself before bringing up the stack; or AUTH_DISABLED=true for testing only)")

_windows: dict[str, deque] = defaultdict(deque)


async def verify_origin(request: Request, call_next):
    """If an origin secret is configured (it isn't, by default, in this minimal setup — see the
    module docstring), only requests carrying the matching header go through."""
    if ORIGIN_VERIFY_SECRET:
        sent = request.headers.get("x-origin-verify", "")
        if not secrets.compare_digest(sent.encode(), ORIGIN_VERIFY_SECRET.encode()):
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    return await call_next(request)


def authenticate(x_api_key: str | None = Header(default=None)) -> str:
    """Checks the API key (constant-time) and returns an identifier for the rate limit."""
    if AUTH_DISABLED:
        return "anonymous"
    if not x_api_key or not any(secrets.compare_digest(x_api_key.encode(), k.encode()) for k in API_KEYS):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    return hashlib.sha256(x_api_key.encode()).hexdigest()[:12]


def rate_limit(client: str = Depends(authenticate)) -> None:
    """One-minute sliding window per key. In memory: only valid for a single instance."""
    if RATE_LIMIT_PER_MINUTE <= 0:
        return
    now = time.monotonic()
    window = _windows[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests", headers={"Retry-After": "60"})
    window.append(now)
