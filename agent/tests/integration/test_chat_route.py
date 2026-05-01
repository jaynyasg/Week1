"""HTTP /agent/chat (scaffold RGV + multi-turn)."""

from __future__ import annotations

import functools
from typing import Annotated

import pytest
from fastapi import Header, Request
from fastapi.testclient import TestClient

from agent.http.app import create_app
from agent.http.deps import get_chat_turn_runner, resolve_agent_role
from agent.runtime.rgv_pipeline import MAX_VERIFY_RETRIES
from agent.services.chat_turn import run_scaffold_chat_turn


@pytest.fixture
def app():
    application = create_app()
    yield application
    application.dependency_overrides.clear()


def _fake_physician(
    _request: Request,
    _authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    return "PHYSICIAN"


def test_chat_missing_authorization_returns_401(app) -> None:
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-1",
                "user_message": "hello",
                "messages": [],
            },
        )
    assert r.status_code == 401


def _verify_always_fail(_state, _text):
    return False, "forced verify failure (graceful degradation)"


def test_chat_graceful_degradation_verified_false_after_retries(app) -> None:
    """HTTP stack returns explicit ``verified: false`` when verify never passes (bounded retries)."""
    app.dependency_overrides[resolve_agent_role] = _fake_physician
    app.dependency_overrides[get_chat_turn_runner] = lambda: functools.partial(
        run_scaffold_chat_turn,
        verify=_verify_always_fail,
    )
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-1",
                "user_message": "Needs grounding but verify will fail.",
                "messages": [],
            },
            headers={"Authorization": "Bearer test"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["verified"] is False
    assert data["verify_retry_count"] == MAX_VERIFY_RETRIES
    notes = " ".join(data["verification_notes"])
    assert "forced verify failure" in notes


def test_chat_scaffold_returns_messages(app) -> None:
    app.dependency_overrides[resolve_agent_role] = _fake_physician
    with TestClient(app) as client:
        r = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-1",
                "user_message": "Summarize last visit.",
                "messages": [],
            },
            headers={"Authorization": "Bearer test"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["verified"] is True
    assert data["verify_retry_count"] == 0
    assert "assistant_message" in data
    msgs = data["messages"]
    assert any(m.get("role") == "user" for m in msgs)
    assert msgs[-1]["role"] == "assistant"


def test_chat_multiturn_carries_history(app) -> None:
    app.dependency_overrides[resolve_agent_role] = _fake_physician
    with TestClient(app) as client:
        first = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-1",
                "user_message": "First question",
                "messages": [],
            },
            headers={"Authorization": "Bearer test", "X-Clinical-Session-Id": "sess-mt"},
        )
        assert first.status_code == 200
        hist = first.json()["messages"]
        second = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-1",
                "user_message": "Follow-up",
                "messages": hist,
            },
            headers={"Authorization": "Bearer test", "X-Clinical-Session-Id": "sess-mt"},
        )
    assert second.status_code == 200
    names = [m.get("content", "")[:20] for m in second.json()["messages"] if m.get("role") == "user"]
    assert any("First question" in str(c) for c in names)
    assert any("Follow-up" in str(c) for c in names)
