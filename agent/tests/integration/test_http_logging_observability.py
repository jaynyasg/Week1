"""Integration: HTTP routes emit structured log extras (Phase 4 observability keys)."""

from __future__ import annotations

import logging
from typing import Annotated

import pytest
from fastapi import Header, Request
from fastapi.testclient import TestClient

from agent.http.deps import resolve_agent_role
from agent.observability.events import LOG_EXTRA_EVENT, LOG_EXTRA_EVENT_TYPE
from agent.observability.taxonomy import CATEGORY_BOUNDARY_REVIEW, CHAT_TURN_COMPLETE


def _fake_physician(
    _request: Request,
    _authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    return "PHYSICIAN"


def _find_record(
    caplog: pytest.LogCaptureFixture,
    *,
    logger_name: str,
    msg_substr: str,
) -> logging.LogRecord | None:
    for r in caplog.records:
        if r.name == logger_name and msg_substr in r.getMessage():
            return r
    return None


def test_post_agent_chat_logs_chat_turn_complete_with_event_fields(
    app, caplog: pytest.LogCaptureFixture
) -> None:
    """``log_agent_event`` uses INFO; records must carry ``event`` and ``event_type``."""
    caplog.set_level(logging.INFO)
    app.dependency_overrides[resolve_agent_role] = _fake_physician
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-log-1",
                "user_message": "Check observability fields.",
                "messages": [],
            },
            headers={"Authorization": "Bearer test"},
        )
    assert r.status_code == 200
    rec = _find_record(
        caplog, logger_name="agent.services.chat_turn", msg_substr="agent_event"
    )
    assert rec is not None, (
        f"expected agent_event log; got: {[r.getMessage() for r in caplog.records]}"
    )
    assert getattr(rec, LOG_EXTRA_EVENT) == CHAT_TURN_COMPLETE
    assert getattr(rec, LOG_EXTRA_EVENT_TYPE) == CHAT_TURN_COMPLETE
    assert getattr(rec, "rgv_duration_ms", 0) >= 0
    assert getattr(rec, "fallback") in ("none", "unverified_response")


def test_post_agent_chat_dual_category_logs_boundary_review(
    app, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    app.dependency_overrides[resolve_agent_role] = _fake_physician
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-cat-1",
                "user_message": "dual_category_demo trigger",
                "messages": [],
            },
            headers={"Authorization": "Bearer test"},
        )
    assert r.status_code == 200
    boundary = _find_record(
        caplog,
        logger_name="agent.services.chat_turn",
        msg_substr=CATEGORY_BOUNDARY_REVIEW,
    )
    assert boundary is not None
    assert getattr(boundary, LOG_EXTRA_EVENT) == CATEGORY_BOUNDARY_REVIEW


def test_post_agent_tools_rbac_403_logs_tool_refusal_with_event_field(
    app, caplog: pytest.LogCaptureFixture
) -> None:
    """RBAC denial triggers ``log_tool_refusal`` at INFO with ``event`` / ``event_type`` extras."""

    async def fake_nurse(
        _request: Request,
        _authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> str:
        return "NURSE"

    caplog.set_level(logging.INFO)
    app.dependency_overrides[resolve_agent_role] = fake_nurse
    with TestClient(app) as client:
        r = client.post(
            "/agent/tools/labs",
            headers={"Authorization": "Bearer test-token"},
        )
    assert r.status_code == 403
    rec = _find_record(caplog, logger_name="agent.http.app", msg_substr="tool_refusal")
    assert rec is not None, (
        f"expected tool_refusal log; got: {[r.getMessage() for r in caplog.records]}"
    )
    assert getattr(rec, LOG_EXTRA_EVENT) == "tool_refusal"
    assert getattr(rec, LOG_EXTRA_EVENT_TYPE) == "tool_refusal"
    assert getattr(rec, "what") == "rbac_tool_denied"
    assert getattr(rec, "cost_envelope") == "unknown"
