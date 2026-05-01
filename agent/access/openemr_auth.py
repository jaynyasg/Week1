"""
Validate OpenEMR session tokens via GET /api/user (see ARCHITECTURE.md auth flow).

OpenEMR installs vary in JSON shape; callers should prefer injecting ``agent_role``
after authoritative mapping in middleware. This module provides a transport helper
plus a small heuristic mapper for tests and bootstrap environments.
"""

from __future__ import annotations

from typing import Any

import httpx


class OpenEMRAuthError(Exception):
    """Missing/invalid session or role could not be resolved to PHYSICIAN|NURSE|ADMIN."""


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


async def fetch_openemr_user_json(
    openemr_base_url: str,
    *,
    authorization_header_value: str,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    """
    GET {base}/api/user with Authorization header (Bearer or session scheme as provided).

    Raises OpenEMRAuthError on non-200 or invalid JSON.
    """
    base = openemr_base_url.rstrip("/")
    url = f"{base}/api/user"
    headers = {"Authorization": authorization_header_value}
    try:
        response = await client.get(url, headers=headers, timeout=30.0)
    except httpx.RequestError as exc:  # pragma: no cover - network
        raise OpenEMRAuthError(f"OpenEMR /api/user request failed: {exc}") from exc

    if response.status_code != 200:
        raise OpenEMRAuthError(
            f"OpenEMR /api/user returned {response.status_code}",
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise OpenEMRAuthError("OpenEMR /api/user returned non-JSON body") from exc
    if not isinstance(data, dict):
        raise OpenEMRAuthError("OpenEMR /api/user JSON must be an object")
    return data


async def validate_session_and_resolve_role(
    openemr_base_url: str,
    *,
    authorization_header_value: str,
    client: httpx.AsyncClient,
) -> str:
    """Fetch /api/user and map to agent role; raises OpenEMRAuthError if denied."""
    payload = await fetch_openemr_user_json(
        openemr_base_url,
        authorization_header_value=authorization_header_value,
        client=client,
    )
    role = map_openemr_payload_to_agent_role(payload)
    if role is None:
        raise OpenEMRAuthError("Could not map OpenEMR user to agent role")
    return role
