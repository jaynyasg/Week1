"""Offline checks for Fly manifest files under deploy/ (no network)."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEPLOY = _REPO_ROOT / "deploy"


def test_fly_openemr_manifest_https_and_role() -> None:
    fly_app = (_DEPLOY / "fly.toml").read_text(encoding="utf-8")
    assert 'app = "clinical-copilot"' in fly_app
    assert "force_https = true" in fly_app


def test_fly_db_manifest_has_no_public_http_service() -> None:
    fly_db = (_DEPLOY / "fly.db.toml").read_text(encoding="utf-8")
    # Literal section only (comments may mention [http_service]).
    assert re.search(r"^\[http_service\]\s*$", fly_db, re.MULTILINE) is None
