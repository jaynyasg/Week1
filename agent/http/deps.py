"""FastAPI dependencies: OpenEMR session -> agent role."""

from __future__ import annotations

import logging
import os
from typing import Annotated

import httpx
from fastapi import Header, HTTPException, Request

from agent.access.openemr_auth import OpenEMRAuthError, validate_session_and_resolve_role
from agent.observability.events import log_agent_event
from agent.observability.taxonomy import (
    DEMO_BYPASS_ACTIVE,
    OPENEMR_AUTH_FAILURE,
    OPENEMR_MISCONFIGURATION,
)
from agent.services.chat_turn import run_scaffold_chat_turn

_LOG = logging.getLogger(__name__)

_DEMO_BYPASS_TRUTHY = frozenset({"1", "true", "yes"})
_DEMO_BYPASS_ROLES = frozenset({"PHYSICIAN", "NURSE", "ADMIN"})


def _demo_bypass_enabled() -> bool:
    """True iff ``AGENT_DEMO_BYPASS`` env is one of {"1","true","yes"} (case-insensitive).

    Factored out of ``resolve_agent_role`` so unit tests can target the env-read
    behavior without spinning up a request. Default (unset/empty/anything else)
    returns False so the production auth path is byte-identical to before.
    """
    raw = os.environ.get("AGENT_DEMO_BYPASS", "")
    return raw.strip().lower() in _DEMO_BYPASS_TRUTHY


def _client_request_id(request: Request | None) -> str | None:
    """Correlation id: middleware ``request.state.request_id`` or inbound headers."""
    if request is None:
        return None
    state = getattr(request, "state", None)
    state_id = getattr(state, "request_id", None) if state is not None else None
    if isinstance(state_id, str) and state_id.strip():
        return state_id.strip()[:128]
    for header_name in ("X-Request-ID", "X-Correlation-ID", "X-Trace-ID"):
        raw = request.headers.get(header_name)
        if raw and raw.strip():
            return raw.strip()[:128]
    return None


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_chat_turn_runner():
    """
    Callable that runs one scaffold RGV chat turn (override in tests).

    Returns ``run_scaffold_chat_turn``; inject a partial or wrapper to swap verify/retrieve.
    Integration overrides: ``agent/tests/integration/test_chat_route.py``.
    """
    return run_scaffold_chat_turn


def get_openemr_base_url(request: Request | None = None) -> str:
    base = os.environ.get("OPENEMR_BASE_URL", "").strip().rstrip("/")
    if not base:
        cid = _client_request_id(request)
        log_agent_event(
            _LOG,
            OPENEMR_MISCONFIGURATION,
            what="openemr_unreachable_config",
            why="OPENEMR_BASE_URL missing_or_empty",
            duration_ms=0.0,
            fallback="none",
            cost_envelope="unknown",
            client_request_id=cid or "none",
        )
        raise HTTPException(
            status_code=500,
            detail="OPENEMR_BASE_URL is not configured",
        )
    return base


async def resolve_agent_role(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    cookie: Annotated[str | None, Header(alias="Cookie")] = None,
    x_agent_demo_role: Annotated[str | None, Header(alias="X-Agent-Demo-Role")] = None,
) -> str:
    """
    Validate OpenEMR session via GET /api/user and map to PHYSICIAN|NURSE|ADMIN.

    Accepts EITHER an ``Authorization`` header (Bearer/OAuth2) OR a ``Cookie``
    header copied from a logged-in OpenEMR browser session (``OpenEMR=...;
    PHPSESSID=...``). At least one must be non-blank; both may be sent together
    and OpenEMR decides which to honor.

    Demo bypass (NOT for production): when ``AGENT_DEMO_BYPASS`` is truthy AND
    ``X-Agent-Demo-Role`` is one of ``PHYSICIAN|NURSE|ADMIN``, this returns the
    supplied role without calling OpenEMR. If the env var is unset, the demo
    header is ignored entirely (default behavior unchanged). If the env var is
    set but the header is missing/invalid, we fall through to the normal
    Authorization/Cookie path so existing flows still work.

    Override this dependency in tests to exercise RBAC without a live OpenEMR.
    """
    if _demo_bypass_enabled() and x_agent_demo_role is not None:
        candidate = x_agent_demo_role.strip().upper()
        if candidate in _DEMO_BYPASS_ROLES:
            log_agent_event(
                _LOG,
                DEMO_BYPASS_ACTIVE,
                what="auth_demo_bypass",
                why="AGENT_DEMO_BYPASS=1",
                role=candidate,
                fallback="none",
                duration_ms=0.0,
                cost_envelope="unknown",
                client_request_id=_client_request_id(request) or "none",
            )
            return candidate

    auth_value = authorization.strip() if authorization and authorization.strip() else None
    cookie_value = cookie.strip() if cookie and cookie.strip() else None
    if auth_value is None and cookie_value is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization or Cookie header",
        )
    base = get_openemr_base_url(request)
    client = get_http_client(request)
    cid = _client_request_id(request) or "none"
    try:
        return await validate_session_and_resolve_role(
            base,
            authorization_header_value=auth_value,
            cookie_header_value=cookie_value,
            client=client,
            request_id=cid if cid != "none" else None,
        )
    except OpenEMRAuthError as exc:
        log_agent_event(
            _LOG,
            OPENEMR_AUTH_FAILURE,
            what="openemr_session_validation_failed",
            why=str(exc)[:500],
            reason_code=getattr(exc, "reason_code", "openemr_auth_error"),
            duration_ms=0.0,
            fallback="none",
            cost_envelope="unknown",
            client_request_id=cid,
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "openemr_auth_failed",
                "reason_code": getattr(exc, "reason_code", "openemr_auth_error"),
                "message": str(exc),
                "request_id": cid,
            },
        ) from exc
