"""Unit tests for ``agent.http.deps`` helpers."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from agent.access.openemr_auth import OpenEMRAuthError
from agent.http.deps import (
    _client_request_id,
    _demo_bypass_enabled,
    effective_openemr_cookie_header,
    get_openemr_base_url,
    resolve_agent_role,
)
from agent.observability.events import LOG_EXTRA_EVENT
from agent.observability.taxonomy import (
    DEMO_BYPASS_ACTIVE,
    OPENEMR_AUTH_FAILURE,
    OPENEMR_MISCONFIGURATION,
)


def test_get_openemr_base_url_raises_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


def test_get_openemr_base_url_raises_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "")
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


@pytest.mark.parametrize(
    "value",
    ["   ", "\t\n  ", "///"],
)
def test_get_openemr_base_url_raises_when_whitespace_or_slash_only(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", value)
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


def test_get_openemr_base_url_strips_trailing_slashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.com/")
    assert get_openemr_base_url() == "https://openemr.example.com"


def test_get_openemr_base_url_strips_multiple_trailing_slashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.com///")
    assert get_openemr_base_url() == "https://openemr.example.com"


def test_get_openemr_base_url_strips_outer_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "  https://host/openemr/  ")
    assert get_openemr_base_url() == "https://host/openemr"


def test_get_openemr_base_url_unchanged_without_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://host/path")
    assert get_openemr_base_url() == "https://host/path"


def test_client_request_id_prefers_first_header() -> None:
    req = MagicMock()
    req.headers.get = lambda name, default=None: {
        "X-Request-ID": "rid",
        "X-Correlation-ID": "cid",
    }.get(name, default)
    assert _client_request_id(req) == "rid"


def test_get_openemr_base_url_misconfig_includes_client_request_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
    caplog.set_level(logging.INFO)
    req = MagicMock()
    req.headers.get = lambda name, default=None: {"X-Request-ID": "unit-req-7"}.get(
        name, default
    )
    with pytest.raises(HTTPException):
        get_openemr_base_url(req)
    mis = [
        r
        for r in caplog.records
        if r.name == "agent.http.deps"
        and getattr(r, LOG_EXTRA_EVENT, None) == OPENEMR_MISCONFIGURATION
    ]
    assert mis and getattr(mis[0], "client_request_id") == "unit-req-7"


# --- Demo bypass --------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("TRUE", True),
        ("True", True),
        ("yes", True),
        ("YES", True),
        ("  yes  ", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("", False),
        ("on", False),
    ],
)
def test_demo_bypass_enabled_truthy_matrix(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("AGENT_DEMO_BYPASS", value)
    assert _demo_bypass_enabled() is expected


def test_demo_bypass_enabled_unset_is_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_DEMO_BYPASS", raising=False)
    assert _demo_bypass_enabled() is False


@pytest.mark.parametrize(
    "cookie,x_browser,expected",
    [
        (None, None, None),
        ("a=1", None, "a=1"),
        (None, "OpenEMR=xyz", "OpenEMR=xyz"),
        ("_ga=1", "OpenEMR=xyz; token_main=1", "_ga=1; OpenEMR=xyz; token_main=1"),
    ],
)
def test_effective_openemr_cookie_header_merges(
    cookie: str | None, x_browser: str | None, expected: str | None
) -> None:
    assert effective_openemr_cookie_header(cookie, x_browser) == expected


@pytest.mark.asyncio
async def test_resolve_agent_role_bypass_short_circuits_without_calling_openemr(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Bypass enabled + valid role header => return role without touching /api/user."""
    monkeypatch.setenv("AGENT_DEMO_BYPASS", "1")
    caplog.set_level(logging.INFO)

    async def _must_not_call(
        *_args, **_kwargs
    ):  # pragma: no cover - asserted not-called
        raise AssertionError(
            "validate_session_and_resolve_role should not be called in bypass path"
        )

    monkeypatch.setattr(
        "agent.http.deps.validate_session_and_resolve_role",
        _must_not_call,
    )

    req = MagicMock()
    req.headers.get = lambda name, default=None: {"X-Request-ID": "demo-1"}.get(
        name, default
    )

    role = await resolve_agent_role(
        req,
        authorization=None,
        cookie=None,
        x_openemr_browser_cookies=None,
        x_agent_demo_role="physician",
    )
    assert role == "PHYSICIAN"

    bypass_records = [
        r
        for r in caplog.records
        if r.name == "agent.http.deps"
        and getattr(r, LOG_EXTRA_EVENT, None) == DEMO_BYPASS_ACTIVE
    ]
    assert bypass_records, "expected an auth_demo_bypass event"
    rec = bypass_records[0]
    assert getattr(rec, "role") == "PHYSICIAN"
    assert getattr(rec, "what") == "auth_demo_bypass"
    assert getattr(rec, "why") == "AGENT_DEMO_BYPASS=1"
    assert getattr(rec, "fallback") == "none"
    assert getattr(rec, "duration_ms") == 0.0
    assert getattr(rec, "cost_envelope") == "unknown"
    assert getattr(rec, "client_request_id") == "demo-1"


@pytest.mark.asyncio
async def test_resolve_agent_role_bypass_invalid_role_falls_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bypass on but role header is junk => fall through to normal validation."""
    monkeypatch.setenv("AGENT_DEMO_BYPASS", "1")
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.test")

    called: dict[str, object] = {}

    async def _fake_validate(
        _base: str,
        *,
        authorization_header_value: str | None = None,
        cookie_header_value: str | None = None,
        client,  # noqa: ARG001
        request_id: str | None = None,  # noqa: ARG001
    ) -> str:
        called["authorization"] = authorization_header_value
        called["cookie"] = cookie_header_value
        return "NURSE"

    monkeypatch.setattr(
        "agent.http.deps.validate_session_and_resolve_role",
        _fake_validate,
    )

    req = MagicMock()
    req.app.state.http_client = MagicMock()
    req.headers.get = lambda _name, default=None: default

    role = await resolve_agent_role(
        req,
        authorization="Bearer abc",
        cookie=None,
        x_openemr_browser_cookies=None,
        x_agent_demo_role="GUEST",
    )
    assert role == "NURSE"
    assert called["authorization"] == "Bearer abc"
    assert called["cookie"] is None


@pytest.mark.asyncio
async def test_resolve_agent_role_bypass_disabled_ignores_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env var unset => X-Agent-Demo-Role is ignored entirely; normal validation runs."""
    monkeypatch.delenv("AGENT_DEMO_BYPASS", raising=False)
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.test")

    async def _fake_validate(
        _base: str,
        *,
        authorization_header_value: str | None = None,
        cookie_header_value: str | None = None,
        client,  # noqa: ARG001
        request_id: str | None = None,  # noqa: ARG001
    ) -> str:
        return "ADMIN"

    monkeypatch.setattr(
        "agent.http.deps.validate_session_and_resolve_role",
        _fake_validate,
    )

    req = MagicMock()
    req.app.state.http_client = MagicMock()
    req.headers.get = lambda _name, default=None: default

    role = await resolve_agent_role(
        req,
        authorization="Bearer abc",
        cookie=None,
        x_openemr_browser_cookies=None,
        x_agent_demo_role="PHYSICIAN",
    )
    assert role == "ADMIN"


@pytest.mark.asyncio
async def test_resolve_agent_role_openemr_failure_emits_event_and_structured_http_exception(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("AGENT_DEMO_BYPASS", raising=False)
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.test")
    caplog.set_level(logging.INFO)

    async def _deny(_base: str, **_kw: object) -> str:
        raise OpenEMRAuthError("bad session", reason_code="e2e_fail")

    monkeypatch.setattr(
        "agent.http.deps.validate_session_and_resolve_role",
        _deny,
    )

    req = MagicMock()
    req.app.state.http_client = MagicMock()
    req.headers.get = lambda name, default=None: {"X-Request-ID": "req-for-log"}.get(
        name, default
    )

    with pytest.raises(HTTPException) as exc_info:
        await resolve_agent_role(
            req,
            authorization="Bearer x",
            cookie=None,
            x_openemr_browser_cookies=None,
            x_agent_demo_role=None,
        )
    assert exc_info.value.status_code == 401
    d = exc_info.value.detail
    assert isinstance(d, dict)
    assert d["error"] == "openemr_auth_failed"
    assert d["reason_code"] == "e2e_fail"
    assert d["request_id"] == "req-for-log"

    auth_fails = [
        r
        for r in caplog.records
        if r.name == "agent.http.deps"
        and getattr(r, LOG_EXTRA_EVENT, None) == OPENEMR_AUTH_FAILURE
    ]
    assert auth_fails and getattr(auth_fails[0], "client_request_id") == "req-for-log"


@pytest.mark.asyncio
async def test_resolve_agent_role_bypass_disabled_no_auth_still_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env var unset, no Authorization/Cookie, but demo header present => still 401."""
    monkeypatch.delenv("AGENT_DEMO_BYPASS", raising=False)

    req = MagicMock()
    req.headers.get = lambda _name, default=None: default

    with pytest.raises(HTTPException) as exc_info:
        await resolve_agent_role(
            req,
            authorization=None,
            cookie=None,
            x_openemr_browser_cookies=None,
            x_agent_demo_role="PHYSICIAN",
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_agent_role_x_openemr_browser_cookies_forwards_to_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Embedded SPA may send only X-OpenEMR-Browser-Cookies (no Cookie header)."""
    monkeypatch.delenv("AGENT_DEMO_BYPASS", raising=False)
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.test")

    called: dict[str, object] = {}

    async def _fake_validate(
        _base: str,
        *,
        authorization_header_value: str | None = None,
        cookie_header_value: str | None = None,
        client,  # noqa: ARG001
        request_id: str | None = None,  # noqa: ARG001
    ) -> str:
        called["cookie"] = cookie_header_value
        called["authorization"] = authorization_header_value
        return "ADMIN"

    monkeypatch.setattr(
        "agent.http.deps.validate_session_and_resolve_role",
        _fake_validate,
    )

    req = MagicMock()
    req.app.state.http_client = MagicMock()
    req.headers.get = lambda _name, default=None: default

    role = await resolve_agent_role(
        req,
        authorization=None,
        cookie=None,
        x_openemr_browser_cookies="OpenEMR=abc; token_main=z",
        x_agent_demo_role=None,
    )
    assert role == "ADMIN"
    assert called["cookie"] == "OpenEMR=abc; token_main=z"
    assert called["authorization"] is None
