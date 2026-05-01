"""HTTP-level RBAC on /agent/tools/{tool_name} (dependency overrides, no live OpenEMR)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent.http.app import create_app
from agent.http.deps import resolve_agent_role


@pytest.fixture
def app():
    application = create_app()
    yield application
    application.dependency_overrides.clear()


def test_health(app) -> None:
    with TestClient(app) as client:
        r = client.get("/agent/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_tool_missing_authorization_returns_401(app) -> None:
    with TestClient(app) as client:
        r = client.post("/agent/tools/demographics")
    assert r.status_code == 401


def test_nurse_allowed_demographics(app) -> None:
    async def fake_role() -> str:
        return "NURSE"

    app.dependency_overrides[resolve_agent_role] = fake_role
    with TestClient(app) as client:
        r = client.post(
            "/agent/tools/demographics",
            headers={"Authorization": "Bearer test-token"},
        )
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "role": "NURSE", "tool": "demographics"}


def test_nurse_denied_labs_returns_403_body(app) -> None:
    async def fake_role() -> str:
        return "NURSE"

    app.dependency_overrides[resolve_agent_role] = fake_role
    with TestClient(app) as client:
        r = client.post(
            "/agent/tools/labs",
            headers={"Authorization": "Bearer test-token"},
        )
    assert r.status_code == 403
    body = r.json()
    assert body["error"] == "tool_refusal"
    assert body["role"] == "NURSE"
    assert body["tool"] == "labs"
    assert "NURSE" in body["message"] and "labs" in body["message"]


def test_admin_denied_medications(app) -> None:
    async def fake_role() -> str:
        return "ADMIN"

    app.dependency_overrides[resolve_agent_role] = fake_role
    with TestClient(app) as client:
        r = client.post(
            "/agent/tools/medications",
            headers={"Authorization": "Bearer test-token"},
        )
    assert r.status_code == 403
    assert r.json()["role"] == "ADMIN"
    assert r.json()["tool"] == "medications"
