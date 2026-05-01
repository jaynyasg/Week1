"""
Gated live integration checks against deployed OpenEMR (real network).

**Never commit tokens.** Copy env from `.env.example` / `deploy/.env.example` into a
local `.env` (gitignored).

Enable the OpenEMR `/api/user` E2E checks with:
  RUN_LIVE_OPENEMR_E2E=1
  OPENEMR_BASE_URL=https://clinical-copilot-v2.fly.dev   # default in .env.example

Real session (asserts 200 + role ∈ {PHYSICIAN, NURSE, ADMIN}) additionally requires
one of:
  OPENEMR_AUTHORIZATION   — full ``Authorization`` header value, e.g. ``Bearer <token>``
  OPENEMR_BEARER_TOKEN    — raw token only; tests send ``Bearer <value>`` if not prefixed

``RUN_LIVE_OPENEMR_TESTS=1`` is still accepted as an alias for the gate flag.

Optional deployed agent smoke (``POST /agent/chat`` via httpx, not TestClient):
  AGENT_BASE_URL=https://your-agent-host.example   # trailing slash optional
  (same OpenEMR auth header as above — chat depends on ``resolve_agent_role``)
"""

from __future__ import annotations

import os

import httpx
import pytest

from agent.access.openemr_auth import OpenEMRAuthError, validate_session_and_resolve_role


def _live_openemr_e2e_enabled() -> bool:
    return bool(
        (os.environ.get("RUN_LIVE_OPENEMR_E2E") or "").strip()
        or (os.environ.get("RUN_LIVE_OPENEMR_TESTS") or "").strip(),
    )


def _openemr_authorization_header() -> str | None:
    """Resolve Authorization header value from env (no secrets in repo)."""
    direct = (os.environ.get("OPENEMR_AUTHORIZATION") or "").strip()
    if direct:
        return direct
    bearer = (os.environ.get("OPENEMR_BEARER_TOKEN") or "").strip()
    if not bearer:
        return None
    if bearer.lower().startswith("bearer "):
        return bearer
    return f"Bearer {bearer}"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _live_openemr_e2e_enabled(),
    reason="set RUN_LIVE_OPENEMR_E2E=1 (or RUN_LIVE_OPENEMR_TESTS=1) for live OpenEMR tests",
)
@pytest.mark.skipif(
    not (os.environ.get("OPENEMR_BASE_URL") or "").strip(),
    reason="OPENEMR_BASE_URL must be set",
)
async def test_live_openemr_rejects_invalid_authorization() -> None:
    base = os.environ["OPENEMR_BASE_URL"].strip().rstrip("/")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        with pytest.raises(OpenEMRAuthError):
            await validate_session_and_resolve_role(
                base,
                authorization_header_value="Bearer invalid-token-for-ci",
                client=client,
            )


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _live_openemr_e2e_enabled(),
    reason="set RUN_LIVE_OPENEMR_E2E=1 (or RUN_LIVE_OPENEMR_TESTS=1) for live OpenEMR tests",
)
@pytest.mark.skipif(
    not (os.environ.get("OPENEMR_BASE_URL") or "").strip(),
    reason="OPENEMR_BASE_URL must be set",
)
@pytest.mark.skipif(
    _openemr_authorization_header() is None,
    reason="set OPENEMR_AUTHORIZATION or OPENEMR_BEARER_TOKEN for valid-session E2E",
)
async def test_live_openemr_valid_token_resolves_rbac_role() -> None:
    """GET {OPENEMR_BASE_URL}/api/user with real Authorization → mappable agent role."""
    base = os.environ["OPENEMR_BASE_URL"].strip().rstrip("/")
    auth = _openemr_authorization_header()
    assert auth is not None
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        role = await validate_session_and_resolve_role(
            base,
            authorization_header_value=auth,
            client=client,
        )
    assert role in ("PHYSICIAN", "NURSE", "ADMIN")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _live_openemr_e2e_enabled(),
    reason="set RUN_LIVE_OPENEMR_E2E=1 (or RUN_LIVE_OPENEMR_TESTS=1) for live OpenEMR tests",
)
@pytest.mark.skipif(
    not (os.environ.get("OPENEMR_BASE_URL") or "").strip(),
    reason="OPENEMR_BASE_URL must be set",
)
async def test_live_openemr_base_url_reachable() -> None:
    """Smoke: deployed OpenEMR answers HTTP without requiring a valid session."""
    base = os.environ["OPENEMR_BASE_URL"].strip().rstrip("/")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(base + "/")
    assert response.status_code < 500


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _live_openemr_e2e_enabled(),
    reason="set RUN_LIVE_OPENEMR_E2E=1 (or RUN_LIVE_OPENEMR_TESTS=1) for live OpenEMR tests",
)
@pytest.mark.skipif(
    not (os.environ.get("AGENT_BASE_URL") or "").strip(),
    reason="set AGENT_BASE_URL to hit deployed POST /agent/chat",
)
@pytest.mark.skipif(
    _openemr_authorization_header() is None,
    reason="set OPENEMR_AUTHORIZATION or OPENEMR_BEARER_TOKEN for agent chat E2E",
)
async def test_live_deployed_agent_chat_smoke() -> None:
    """POST {AGENT_BASE_URL}/agent/chat with same OpenEMR session the app uses."""
    agent_base = os.environ["AGENT_BASE_URL"].strip().rstrip("/")
    auth = _openemr_authorization_header()
    assert auth is not None
    url = f"{agent_base}/agent/chat"
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.post(
            url,
            headers={"Authorization": auth},
            json={
                "patient_id": "live-e2e-patient",
                "user_message": "ping",
                "messages": [],
            },
        )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "assistant_message" in data
    assert isinstance(data.get("assistant_message"), str)
