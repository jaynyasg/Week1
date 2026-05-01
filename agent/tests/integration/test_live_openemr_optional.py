"""
Optional live checks against deployed OpenEMR (network).

Enable with:
  RUN_LIVE_OPENEMR_TESTS=1
  OPENEMR_BASE_URL=https://clinical-copilot-v2.fly.dev
"""

from __future__ import annotations

import os

import httpx
import pytest

from agent.access.openemr_auth import OpenEMRAuthError, fetch_openemr_user_json


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_OPENEMR_TESTS"),
    reason="set RUN_LIVE_OPENEMR_TESTS=1 to run network tests",
)
@pytest.mark.skipif(
    not (os.environ.get("OPENEMR_BASE_URL") or "").strip(),
    reason="OPENEMR_BASE_URL must be set",
)
async def test_live_openemr_rejects_invalid_authorization() -> None:
    base = os.environ["OPENEMR_BASE_URL"].strip().rstrip("/")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        with pytest.raises(OpenEMRAuthError):
            await fetch_openemr_user_json(
                base,
                authorization_header_value="Bearer invalid-token-for-ci",
                client=client,
            )
