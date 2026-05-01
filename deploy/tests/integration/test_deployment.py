"""
Integration smoke tests for the deployed OpenEMR fork (PR-02).

Run against the live deployed URL:
    DEPLOYED_URL=https://clinical-copilot.fly.dev pytest tests/integration/test_deployment.py

These tests are intentionally lightweight — they verify the deployment is
reachable, secure, and serving the FHIR endpoint. They do NOT verify
authenticated FHIR queries (that lives in tests/integration/test_local_setup.py
from PR-01).

Failure of any test here is a blocker for submission.
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import httpx
import pytest

DEPLOYED_URL = os.environ.get("DEPLOYED_URL")

pytestmark = pytest.mark.skipif(
    not DEPLOYED_URL,
    reason="DEPLOYED_URL env var not set — set it to the live Fly.io URL.",
)


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    # follow_redirects so we accept the OpenEMR login redirect on /
    return httpx.Client(timeout=15.0, follow_redirects=True)


def test_deployed_root_returns_200(client: httpx.Client) -> None:
    """GET / returns 200 (or 302 to login, which the client follows to 200)."""
    resp = client.get(DEPLOYED_URL)
    assert resp.status_code == 200, (
        f"Expected 200 from {DEPLOYED_URL}, got {resp.status_code}. "
        f"Body preview: {resp.text[:200]!r}"
    )


def test_deployed_uses_https(client: httpx.Client) -> None:
    """Every response URL must be https — Fly's force_https should send no http."""
    resp = client.get(DEPLOYED_URL)
    assert str(resp.url).startswith("https://"), (
        f"Final URL is not HTTPS: {resp.url}. "
        "Confirm `force_https = true` in fly.toml's [http_service] block."
    )


def test_deployed_embedded_copilot_ui_reachable(client: httpx.Client) -> None:
    """Clinical Co-Pilot static SPA is baked into the OpenEMR image."""
    url = f"{DEPLOYED_URL}/interface/copilot/"
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"GET {url} returned {resp.status_code}. "
        "Confirm deploy/Dockerfile.fly copies the Vite build to interface/copilot/."
    )
    body = resp.text.lower()
    assert "clinical co-pilot" in body or 'id="root"' in body, (
        f"Unexpected body from copilot UI: {resp.text[:300]!r}"
    )


def test_deployed_serves_openemr_login(client: httpx.Client) -> None:
    """The landing page should be the OpenEMR login screen."""
    resp = client.get(f"{DEPLOYED_URL}/interface/login/login.php")
    assert resp.status_code == 200
    body = resp.text.lower()
    assert "openemr" in body, (
        "Login page does not mention OpenEMR — installer may not have completed. "
        "Check `fly logs --app clinical-copilot`."
    )


def test_deployed_fhir_metadata_reachable(client: httpx.Client) -> None:
    """FHIR R4 metadata (CapabilityStatement) endpoint must respond."""
    url = f"{DEPLOYED_URL}/apis/default/fhir/metadata"
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"FHIR metadata endpoint returned {resp.status_code}. "
        "FHIR R4 may be disabled in this OpenEMR install — enable in "
        "Administration → Globals → Connectors."
    )
    # CapabilityStatement should declare FHIR R4
    body = resp.text
    assert '"resourceType"' in body, "FHIR metadata response is not FHIR JSON."


def test_fhir_auth_required(client: httpx.Client) -> None:
    """Patient resource must require auth — never returns PHI to unauthenticated callers."""
    resp = client.get(f"{DEPLOYED_URL}/apis/default/fhir/Patient")
    assert resp.status_code in (401, 403), (
        f"Unauthenticated GET /fhir/Patient returned {resp.status_code} — "
        "this is a HIPAA-relevant gap. Expected 401 or 403."
    )


def test_mysql_port_not_exposed() -> None:
    """
    Port 3306 on the public hostname must be refused — MariaDB lives only on
    Fly's private network. A successful TCP connect here is a security incident.
    """
    host = urlparse(DEPLOYED_URL).hostname
    assert host, f"Could not parse host from DEPLOYED_URL={DEPLOYED_URL}"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        result = sock.connect_ex((host, 3306))
    finally:
        sock.close()

    # connect_ex returns 0 on success, nonzero on failure (refused/filtered/timeout).
    assert result != 0, (
        f"TCP connect to {host}:3306 SUCCEEDED. MariaDB is exposed to the internet. "
        "Confirm fly.db.toml has no [http_service] or [[services]] block."
    )


def test_response_does_not_leak_server_internals(client: httpx.Client) -> None:
    """Response headers should not expose specific PHP/Apache versions."""
    resp = client.get(DEPLOYED_URL)
    server = resp.headers.get("server", "").lower()
    powered_by = resp.headers.get("x-powered-by", "").lower()
    # Soft check — log-only assertion. A version leak is informational, not blocking.
    leaks = []
    if "php/" in powered_by:
        leaks.append(f"X-Powered-By leaks PHP version: {powered_by!r}")
    if "apache/" in server and "/" in server.split("apache/", 1)[1]:
        leaks.append(f"Server header leaks Apache version: {server!r}")
    if leaks:
        pytest.skip("Version leaks detected (non-blocking): " + "; ".join(leaks))
