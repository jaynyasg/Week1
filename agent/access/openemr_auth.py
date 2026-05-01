"""
Validate OpenEMR session tokens via GET /api/user (see ARCHITECTURE.md auth flow).

OpenEMR installs vary in JSON shape; callers should prefer injecting ``agent_role``
after authoritative mapping in middleware. This module provides a transport helper
plus a small heuristic mapper for tests and bootstrap environments.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class OpenEMRAuthError(Exception):
    """Missing/invalid session or role could not be resolved to PHYSICIAN|NURSE|ADMIN."""

    def __init__(self, message: str, *, reason_code: str = "openemr_auth_error") -> None:
        super().__init__(message)
        self.reason_code = reason_code


def map_openemr_payload_to_agent_role(payload: dict[str, Any]) -> str | None:
    """
    Map /api/user JSON to PHYSICIAN | NURSE | ADMIN, or None if unknown.

    Priority:
    1. Explicit ``agent_role`` / ``copilot_role`` (uppercased).
    2. ``groups`` / ``acl_groups`` string list heuristics (site-tunable).
    """
    explicit = payload.get("agent_role") or payload.get("copilot_role")
    if isinstance(explicit, str):
        u = explicit.strip().upper()
        if u in ("PHYSICIAN", "NURSE", "ADMIN"):
            return u

    groups = payload.get("groups") or payload.get("acl_groups") or []
    if isinstance(groups, str):
        groups = [groups]
    if not isinstance(groups, list):
        groups = []

    gl = [str(g).lower() for g in groups]
    if any("admin" in g for g in gl):
        return "ADMIN"
    if any("nurse" in g for g in gl):
        return "NURSE"
    if any(x in g for g in gl for x in ("physician", "phys", "doctor", "md")):
        return "PHYSICIAN"
    return None


def _openemr_http_timeout_seconds() -> float:
    raw = (os.environ.get("OPENEMR_HTTP_TIMEOUT_SECONDS") or "30").strip() or "30"
    return max(1.0, float(raw))


async def fetch_openemr_user_json(
    openemr_base_url: str,
    *,
    authorization_header_value: str | None = None,
    cookie_header_value: str | None = None,
    client: httpx.AsyncClient,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    GET {base}/api/user with ``Authorization`` and/or ``Cookie`` forwarded.

    Either ``authorization_header_value`` (Bearer or session scheme) **or**
    ``cookie_header_value`` (raw ``Cookie`` header from a logged-in OpenEMR
    browser session) must be a non-blank string. If both are provided, both
    are sent and OpenEMR decides which to honor.

    Raises ``OpenEMRAuthError`` on missing credentials, non-200, or invalid JSON.
    """
    auth_value = (authorization_header_value or "").strip()
    cookie_value = (cookie_header_value or "").strip()
    if not auth_value and not cookie_value:
        raise OpenEMRAuthError(
            "OpenEMR /api/user call requires Authorization or Cookie header",
            reason_code="missing_credentials",
        )

    base = openemr_base_url.rstrip("/")
    url = f"{base}/api/user"
    headers: dict[str, str] = {}
    if auth_value:
        headers["Authorization"] = auth_value
    if cookie_value:
        headers["Cookie"] = cookie_value
    rid = (request_id or "").strip()[:128]
    if rid:
        headers["X-Request-ID"] = rid
    try:
        response = await client.get(url, headers=headers, timeout=_openemr_http_timeout_seconds())
    except httpx.RequestError as exc:  # pragma: no cover - network
        raise OpenEMRAuthError(
            f"OpenEMR /api/user request failed: {exc}",
            reason_code="upstream_unreachable",
        ) from exc

    if response.status_code != 200:
        raise OpenEMRAuthError(
            f"OpenEMR /api/user returned {response.status_code}",
            reason_code=f"openemr_http_{response.status_code}",
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise OpenEMRAuthError(
            "OpenEMR /api/user returned non-JSON body",
            reason_code="invalid_json",
        ) from exc
    if not isinstance(data, dict):
        raise OpenEMRAuthError(
            "OpenEMR /api/user JSON must be an object",
            reason_code="invalid_payload_shape",
        )
    return data


async def validate_session_and_resolve_role(
    openemr_base_url: str,
    *,
    authorization_header_value: str | None = None,
    cookie_header_value: str | None = None,
    client: httpx.AsyncClient,
    request_id: str | None = None,
) -> str:
    """Fetch /api/user and map to agent role; raises ``OpenEMRAuthError`` if denied.

    Accepts ``Authorization`` only, ``Cookie`` only, or both. At least one must
    be non-blank or ``OpenEMRAuthError`` is raised before any HTTP call.
    """
    payload = await fetch_openemr_user_json(
        openemr_base_url,
        authorization_header_value=authorization_header_value,
        cookie_header_value=cookie_header_value,
        client=client,
        request_id=request_id,
    )
    role = map_openemr_payload_to_agent_role(payload)
    if role is None:
        raise OpenEMRAuthError(
            "Could not map OpenEMR user to agent role",
            reason_code="role_mapping_failed",
        )
    return role
