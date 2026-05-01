"""FastAPI dependencies: OpenEMR session -> agent role."""

from __future__ import annotations

import logging
import os
from typing import Annotated

import httpx
from fastapi import Header, HTTPException, Request

from agent.access.openemr_auth import OpenEMRAuthError, validate_session_and_resolve_role
from agent.observability.events import log_agent_event
from agent.observability.taxonomy import OPENEMR_MISCONFIGURATION
from agent.services.chat_turn import run_scaffold_chat_turn

_LOG = logging.getLogger(__name__)


def _client_request_id(request: Request | None) -> str | None:
    """Prefer inbound correlation headers for operator log joins (no secrets)."""
    if request is None:
        return None
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
) -> str:
    """
    Validate OpenEMR session via GET /api/user and map to PHYSICIAN|NURSE|ADMIN.

    Override this dependency in tests to exercise RBAC without a live OpenEMR.
    """
    if not authorization or not authorization.strip():
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    base = get_openemr_base_url(request)
    client = get_http_client(request)
    try:
        return await validate_session_and_resolve_role(
            base,
            authorization_header_value=authorization.strip(),
            client=client,
        )
    except OpenEMRAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
