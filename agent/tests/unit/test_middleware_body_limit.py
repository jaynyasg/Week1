"""Request body size guard (Content-Length pre-check)."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from agent.http.middleware_body_limit import (
    body_too_large_response,
    max_request_body_bytes,
)


async def _empty_receive() -> dict:
    return {"type": "http.request"}


def _post_scope(content_length: int) -> dict:
    return {
        "type": "http",
        "asgi": {"spec_version": "2.0", "version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "headers": [(b"content-length", str(content_length).encode())],
        "scheme": "http",
        "path": "/agent/chat",
        "raw_path": b"/agent/chat",
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }


def test_body_too_large_returns_413_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_MAX_BODY_BYTES", "100")
    assert max_request_body_bytes() == 100
    req = Request(_post_scope(500), _empty_receive)
    resp = body_too_large_response(req)
    assert resp is not None
    assert resp.status_code == 413
    body = resp.body
    assert b"payload_too_large" in body


def test_body_within_limit_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_MAX_BODY_BYTES", "10000")
    req = Request(_post_scope(50), _empty_receive)
    assert body_too_large_response(req) is None


def test_get_requests_not_checked() -> None:
    scope = _post_scope(999999)
    scope["method"] = "GET"
    req = Request(scope, _empty_receive)
    assert body_too_large_response(req) is None
