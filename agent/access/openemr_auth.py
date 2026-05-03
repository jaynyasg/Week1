"""
Validate OpenEMR credentials for the Clinical Co-Pilot.

- **Browser session (Cookie)**: GET the PHP ``copilot_session_probe`` endpoint
  (session cookies from the OpenEMR UI). OpenEMR's Standard REST ``GET /api/user``
  is **admin-scoped** and OAuth Bearer-only; it does not accept UI cookies.

- **Bearer token**: GET ``/apis/{site}/api/user`` (Standard API base), same as
  OpenEMR docs — typically requires appropriate OAuth scopes (often admin for
  this route).

See ARCHITECTURE.md auth flow; ``map_openemr_payload_to_agent_role`` maps JSON to
``PHYSICIAN|NURSE|ADMIN``.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from agent.observability.metrics_counters import inc_openemr_auth_failure


class OpenEMRAuthError(Exception):
    """Missing/invalid session or role could not be resolved to PHYSICIAN|NURSE|ADMIN."""

    def __init__(
        self, message: str, *, reason_code: str = "openemr_auth_error"
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        inc_openemr_auth_failure()


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


def _openemr_site_id() -> str:
    return (os.environ.get("OPENEMR_SITE_ID") or "default").strip() or "default"


def _session_validate_path() -> str:
    raw = (
        os.environ.get("OPENEMR_SESSION_VALIDATE_PATH")
        or "/interface/copilot_session_probe.php"
    ).strip()
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw


def _validation_url_and_target_name(
    openemr_base_url: str,
    *,
    has_cookie: bool,
) -> tuple[str, str]:
    """Return (url, short name for error strings)."""
    base = openemr_base_url.rstrip("/")
    if has_cookie:
        return f"{base}{_session_validate_path()}", "OpenEMR session probe"
    site = _openemr_site_id()
    return f"{base}/apis/{site}/api/user", "OpenEMR Standard API GET /api/user"


def normalize_openemr_user_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten Standard API ``data`` wrappers so role mapping sees ``groups`` / ``acl``."""
    inner = data.get("data")
    if isinstance(inner, list) and len(inner) == 1 and isinstance(inner[0], dict):
        row: dict[str, Any] = dict(inner[0])
    elif isinstance(inner, dict):
        row = dict(inner)
    else:
        return data
    if "groups" not in row and "acl" in row:
        acl = row.get("acl")
        if isinstance(acl, list):
            row["groups"] = acl
    return row


async def fetch_openemr_user_json(
    openemr_base_url: str,
    *,
    authorization_header_value: str | None = None,
    cookie_header_value: str | None = None,
    client: httpx.AsyncClient,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Validate OpenEMR and return a JSON object suitable for ``map_openemr_payload_to_agent_role``.

    If a ``Cookie`` header is present, validates via the PHP session probe
    (UI login). Otherwise uses Standard API ``GET /apis/{site}/api/user`` with
    ``Authorization`` (Bearer).

    Raises ``OpenEMRAuthError`` on missing credentials, non-200, or invalid JSON.
    """
    auth_value = (authorization_header_value or "").strip()
    cookie_value = (cookie_header_value or "").strip()
    if not auth_value and not cookie_value:
        raise OpenEMRAuthError(
            "OpenEMR validation requires Authorization or Cookie header",
            reason_code="missing_credentials",
        )

    has_cookie = bool(cookie_value)
    url, target_name = _validation_url_and_target_name(
        openemr_base_url, has_cookie=has_cookie
    )
    headers: dict[str, str] = {}
    if auth_value:
        headers["Authorization"] = auth_value
    if cookie_value:
        headers["Cookie"] = cookie_value
    rid = (request_id or "").strip()[:128]
    if rid:
        headers["X-Request-ID"] = rid
    try:
        response = await client.get(
            url, headers=headers, timeout=_openemr_http_timeout_seconds()
        )
    except httpx.RequestError as exc:  # pragma: no cover - network
        raise OpenEMRAuthError(
            f"{target_name} request failed: {exc}",
            reason_code="upstream_unreachable",
        ) from exc

    if response.status_code != 200:
        raise OpenEMRAuthError(
            f"{target_name} returned {response.status_code}",
            reason_code=f"openemr_http_{response.status_code}",
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise OpenEMRAuthError(
            f"{target_name} returned non-JSON body",
            reason_code="invalid_json",
        ) from exc
    if not isinstance(data, dict):
        raise OpenEMRAuthError(
            f"{target_name} JSON must be an object",
            reason_code="invalid_payload_shape",
        )
    if has_cookie:
        return data
    return normalize_openemr_user_payload(data)


async def validate_session_and_resolve_role(
    openemr_base_url: str,
    *,
    authorization_header_value: str | None = None,
    cookie_header_value: str | None = None,
    client: httpx.AsyncClient,
    request_id: str | None = None,
) -> str:
    """Fetch user context and map to agent role; raises ``OpenEMRAuthError`` if denied."""
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
