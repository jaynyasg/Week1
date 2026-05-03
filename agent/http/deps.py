"""FastAPI dependencies: OpenEMR session -> agent role."""

from __future__ import annotations

import logging
import os
from typing import Annotated
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import Header, HTTPException, Request

from agent.access.openemr_auth import (
    OpenEMRAuthError,
    validate_session_and_resolve_role,
)
from agent.access.rbac import canonical_agent_role
from agent.observability.events import log_agent_event
from agent.observability.metrics_counters import (
    inc_client_missing_credentials,
    inc_openemr_misconfiguration,
)
from agent.observability.taxonomy import (
    CLIENT_MISSING_CREDENTIALS,
    DEMO_BYPASS_ACTIVE,
    OPENEMR_AUTH_FAILURE,
    OPENEMR_MISCONFIGURATION,
)
from agent.services.chat_turn import run_scaffold_chat_turn

_LOG = logging.getLogger(__name__)

_DEMO_BYPASS_TRUTHY = frozenset({"1", "true", "yes"})


def _normalize_openemr_base_url_value(raw: str) -> str:
    """Strip outer slashes and fix ``…/apis/<site_id>`` pasted as the base URL.

    Session probe paths are ``{origin}/interface/...``; if ``OPENEMR_BASE_URL`` is set
    to the Standard API root (``https://host/apis/default``), the probe becomes a
    non-existent URL and OpenEMR returns 401/404.
    """
    u = raw.strip().rstrip("/")
    if not u:
        return u
    parsed = urlparse(u)
    segs = [s for s in parsed.path.split("/") if s]
    if len(segs) == 2 and segs[0] == "apis":
        trimmed = urlunparse(
            (parsed.scheme, parsed.netloc, "", "", "", ""),
        ).rstrip("/")
        return trimmed or u
    return u


_DEMO_BYPASS_ROLES = frozenset({"PHYSICIAN", "NURSE", "ADMIN", "CLINICIAN"})


def _normalize_openemr_cookie_header_value(raw: str) -> str:
    """Keep a single ``OpenEMR=`` pair (last wins) so PHP does not see duplicates.

    Merging ``Cookie`` + ``X-OpenEMR-Browser-Cookies`` often yields two ``OpenEMR=``
    assignments; PHP typically picks the first, which may be stale or empty.
    """
    chunks = [p.strip() for p in raw.split(";") if p.strip()]
    if not chunks:
        return ""
    openemr_val: str | None = None
    rest: list[str] = []
    for ch in chunks:
        if "=" not in ch:
            rest.append(ch)
            continue
        name, value = ch.split("=", 1)
        if name.strip().lower() == "openemr":
            openemr_val = value
        else:
            rest.append(ch)
    if openemr_val is None:
        return "; ".join(chunks)
    return "; ".join([*rest, f"OpenEMR={openemr_val}"])


def effective_openemr_cookie_header(
    cookie: str | None,
    x_openemr_browser_cookies: str | None,
) -> str | None:
    """Merge ``Cookie`` and SPA-supplied ``document.cookie`` for OpenEMR validation.

    Embedded co-pilot may run where the reverse proxy omits cookies on the upstream
    request, or where path rules prevent the ``OpenEMR=`` cookie from attaching to
    ``fetch``. The SPA can send ``X-OpenEMR-Browser-Cookies`` (OpenEMR core session
    is not HttpOnly) so the agent still forwards a session to the PHP probe.

    ``OpenEMR=`` is deduplicated (last value wins) after merging so PHP receives one
    session id.
    """
    c = (cookie or "").strip()
    x = (x_openemr_browser_cookies or "").strip()
    if not c and not x:
        return None
    if not x:
        merged = c
    elif not c:
        merged = x
    elif "openemr=" in x.lower():
        merged = f"{c}; {x}"
    else:
        merged = c
    out = _normalize_openemr_cookie_header_value(merged).strip()
    return out or None


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
    base = _normalize_openemr_base_url_value(os.environ.get("OPENEMR_BASE_URL", ""))
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
        inc_openemr_misconfiguration()
        raise HTTPException(
            status_code=500,
            detail="OPENEMR_BASE_URL is not configured",
        )
    return base


async def resolve_agent_role(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    cookie: Annotated[str | None, Header(alias="Cookie")] = None,
    x_openemr_browser_cookies: Annotated[
        str | None, Header(alias="X-OpenEMR-Browser-Cookies")
    ] = None,
    x_agent_demo_role: Annotated[str | None, Header(alias="X-Agent-Demo-Role")] = None,
) -> str:
    """
    Validate OpenEMR and map to PHYSICIAN|NURSE|ADMIN (``CLINICIAN`` becomes ``NURSE``).

    With a ``Cookie`` header (and optionally ``X-OpenEMR-Browser-Cookies`` from the
    embedded SPA mirroring ``document.cookie``), validates the UI PHP session via
    ``OPENEMR_SESSION_VALIDATE_PATH`` (default ``/interface/copilot_session_probe.php``).
    With ``Authorization`` only, calls Standard API ``GET /apis/{OPENEMR_SITE_ID}/api/user``
    (Bearer). Both headers may be sent; when a cookie is present, the session probe
    is used (cookies drive embedded co-pilot auth).

    Demo bypass (NOT for production): when ``AGENT_DEMO_BYPASS`` is truthy AND
    ``X-Agent-Demo-Role`` is one of ``PHYSICIAN|NURSE|ADMIN|CLINICIAN``, this returns
    the normalized role (``CLINICIAN`` → ``NURSE``) without calling OpenEMR. If the env var is unset, the demo
    header is ignored entirely (default behavior unchanged). If the env var is
    set but the header is missing/invalid, we fall through to the normal
    Authorization/Cookie path so existing flows still work.

    Override this dependency in tests to exercise RBAC without a live OpenEMR.
    """
    if _demo_bypass_enabled() and x_agent_demo_role is not None:
        candidate = x_agent_demo_role.strip().upper()
        if candidate in _DEMO_BYPASS_ROLES:
            normalized = canonical_agent_role(candidate)
            log_agent_event(
                _LOG,
                DEMO_BYPASS_ACTIVE,
                what="auth_demo_bypass",
                why="AGENT_DEMO_BYPASS=1",
                role=normalized,
                fallback="none",
                duration_ms=0.0,
                cost_envelope="unknown",
                client_request_id=_client_request_id(request) or "none",
            )
            return normalized

    auth_value = (
        authorization.strip() if authorization and authorization.strip() else None
    )
    merged_cookie = effective_openemr_cookie_header(cookie, x_openemr_browser_cookies)
    cookie_value = merged_cookie.strip() if merged_cookie and merged_cookie.strip() else None
    if auth_value is None and cookie_value is None:
        cid = _client_request_id(request) or "none"
        log_agent_event(
            _LOG,
            CLIENT_MISSING_CREDENTIALS,
            what="http_request_missing_credentials",
            why="no_authorization_and_no_cookie",
            duration_ms=0.0,
            fallback="none",
            cost_envelope="unknown",
            client_request_id=cid,
        )
        inc_client_missing_credentials()
        raise HTTPException(
            status_code=401,
            detail=(
                "Missing Authorization or Cookie header "
                "(embedded OpenEMR UI may send X-OpenEMR-Browser-Cookies)"
            ),
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
