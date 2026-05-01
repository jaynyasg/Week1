"""Body limits, readiness, metrics, and optional rate limits (TestClient / localhost)."""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Header, Request
from fastapi.testclient import TestClient

from agent.http.app import create_app
from agent.http.deps import resolve_agent_role
from agent.observability.metrics_counters import reset_counters_for_testing


def _fake_physician(
    _request: Request,
    _authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    _cookie: Annotated[str | None, Header(alias="Cookie")] = None,
) -> str:
    return "PHYSICIAN"


def test_health_ready_and_metrics_exist() -> None:
    reset_counters_for_testing()
    app = create_app()
    with TestClient(app) as client:
        h = client.get("/agent/health")
        assert h.status_code == 200
        assert h.json() == {"status": "ok"}
        r = client.get("/agent/health/ready")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert "openemr_base_url_configured" in body
        m = client.get("/agent/metrics")
        assert m.status_code == 200
        assert "clinical_agent_up" in m.text
        for name in (
            "chat_turns_total",
            "tool_refusals_total",
            "verify_failures_total",
            "rgv_degraded_total",
            "category_boundary_flags_total",
            "openemr_auth_failures_total",
            "openemr_misconfiguration_total",
            "client_missing_credentials_total",
        ):
            assert name in m.text
            assert f"{name} 0" in m.text


def test_chat_rate_limit_enforced_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_RATE_LIMIT_CHAT", "2/minute")
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.test")
    application = create_app()
    application.dependency_overrides[resolve_agent_role] = _fake_physician
    with TestClient(application) as client:
        for _ in range(2):
            r = client.post(
                "/agent/chat",
                json={"patient_id": "p", "user_message": "hi", "messages": []},
                headers={"Authorization": "Bearer t"},
            )
            assert r.status_code == 200, r.text
        r3 = client.post(
            "/agent/chat",
            json={"patient_id": "p", "user_message": "three", "messages": []},
            headers={"Authorization": "Bearer t"},
        )
    assert r3.status_code == 429


@pytest.mark.skipif(
    not __import__("os").environ.get("RUN_LOAD_TEST"),
    reason="set RUN_LOAD_TEST=1 for localhost burst smoke (sequential TestClient posts)",
)
def test_chat_burst_localhost_only(app) -> None:
    """Sequential burst against TestClient — not a real load tool; guards obvious regressions."""
    app.dependency_overrides[resolve_agent_role] = _fake_physician
    with TestClient(app) as client:
        for i in range(25):
            r = client.post(
                "/agent/chat",
                json={"patient_id": "p", "user_message": f"m{i}", "messages": []},
                headers={"Authorization": "Bearer t"},
            )
            assert r.status_code == 200, r.text
