"""Integration: dependency paths emit structured logs with minimum operator fields."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from agent.access.openemr_auth import OpenEMRAuthError
from agent.http.app import create_app
from agent.observability.events import LOG_EXTRA_EVENT_TYPE
from agent.observability.metrics_counters import reset_counters_for_testing, snapshot
from agent.observability.taxonomy import (
    CLIENT_MISSING_CREDENTIALS,
    DEMO_BYPASS_ACTIVE,
    OPENEMR_AUTH_FAILURE,
    OPENEMR_MISCONFIGURATION,
)


@pytest.fixture
def caplog_info(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.INFO)
    return caplog


def test_missing_credentials_logs_minimum_fields_and_metric(
    monkeypatch: pytest.MonkeyPatch,
    caplog_info: pytest.LogCaptureFixture,
) -> None:
    reset_counters_for_testing()
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.contract.test")
    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={"patient_id": "p", "user_message": "hi", "messages": []},
        )
    assert r.status_code == 401
    hits = [
        x
        for x in caplog_info.records
        if getattr(x, LOG_EXTRA_EVENT_TYPE, None) == CLIENT_MISSING_CREDENTIALS
    ]
    assert hits
    rec = hits[0]
    assert getattr(rec, "what") == "http_request_missing_credentials"
    assert getattr(rec, "why") == "no_authorization_and_no_cookie"
    assert getattr(rec, "fallback") == "none"
    assert getattr(rec, "cost_envelope") == "unknown"
    assert snapshot()["client_missing_credentials_total"] >= 1


def test_openemr_misconfiguration_logs_minimum_fields(
    monkeypatch: pytest.MonkeyPatch,
    caplog_info: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={"patient_id": "p", "user_message": "hi", "messages": []},
            headers={"Authorization": "Bearer t"},
        )
    assert r.status_code == 500
    hits = [
        x
        for x in caplog_info.records
        if getattr(x, LOG_EXTRA_EVENT_TYPE, None) == OPENEMR_MISCONFIGURATION
    ]
    assert hits
    rec = hits[0]
    assert getattr(rec, "what") == "openemr_unreachable_config"
    assert "OPENEMR_BASE_URL" in str(getattr(rec, "why", ""))


def test_openemr_auth_failure_logs_minimum_fields(
    monkeypatch: pytest.MonkeyPatch,
    caplog_info: pytest.LogCaptureFixture,
) -> None:
    async def _fail(*_a, **_kw):
        raise OpenEMRAuthError("session rejected", reason_code="openemr_http_401")

    monkeypatch.setattr(
        "agent.http.deps.validate_session_and_resolve_role",
        _fail,
    )
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.contract.test")
    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={"patient_id": "p", "user_message": "hi", "messages": []},
            headers={"Authorization": "Bearer token"},
        )
    assert r.status_code == 401
    hits = [
        x
        for x in caplog_info.records
        if getattr(x, LOG_EXTRA_EVENT_TYPE, None) == OPENEMR_AUTH_FAILURE
    ]
    assert hits
    rec = hits[0]
    assert getattr(rec, "what") == "openemr_session_validation_failed"
    assert getattr(rec, "reason_code") == "openemr_http_401"
    assert getattr(rec, "fallback") == "none"
    assert getattr(rec, "cost_envelope") == "unknown"


def test_demo_bypass_logs_minimum_fields(
    monkeypatch: pytest.MonkeyPatch,
    caplog_info: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("AGENT_DEMO_BYPASS", "1")
    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={"patient_id": "p", "user_message": "hi", "messages": []},
            headers={"X-Agent-Demo-Role": "PHYSICIAN"},
        )
    assert r.status_code == 200, r.text
    hits = [
        x
        for x in caplog_info.records
        if getattr(x, LOG_EXTRA_EVENT_TYPE, None) == DEMO_BYPASS_ACTIVE
    ]
    assert hits
    rec = hits[0]
    assert getattr(rec, "what") == "auth_demo_bypass"
    assert getattr(rec, "why") == "AGENT_DEMO_BYPASS=1"
    assert getattr(rec, "role") == "PHYSICIAN"
    assert getattr(rec, "fallback") == "none"
    assert getattr(rec, "cost_envelope") == "unknown"
