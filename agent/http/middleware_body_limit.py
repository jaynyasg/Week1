"""Reject oversized request bodies using ``Content-Length`` (cheap pre-read check)."""

from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

_LOG_METHODS = frozenset({"POST", "PUT", "PATCH"})


def max_request_body_bytes() -> int:
    raw = (os.environ.get("AGENT_MAX_BODY_BYTES") or "262144").strip() or "262144"
    # Floor 64 so operators/tests can set a small cap; avoid accidental "0" disabling checks.
    return max(64, int(raw))


def body_too_large_response(request: Request) -> JSONResponse | None:
    """Return a 413 response if ``Content-Length`` exceeds the cap; else ``None``."""
    if request.method not in _LOG_METHODS:
        return None
    limit = max_request_body_bytes()
    cl = request.headers.get("content-length")
    if not cl:
        return None
    try:
        n = int(cl)
    except ValueError:
        return None
    if n > limit:
        return JSONResponse(
            status_code=413,
            content={
                "detail": {
                    "error": "payload_too_large",
                    "max_bytes": limit,
                    "content_length": n,
                },
            },
        )
    return None


async def max_body_middleware(request: Request, call_next):
    early = body_too_large_response(request)
    if early is not None:
        return early
    return await call_next(request)
