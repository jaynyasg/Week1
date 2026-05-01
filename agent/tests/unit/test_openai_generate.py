"""OpenAI-backed generate step (mocked SDK)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.runtime.rgv_pipeline import ClinicalTurnState
from agent.services.chat_turn import scaffold_generate
from agent.services.openai_generate import build_chat_messages, complete_chat_openai


def test_build_chat_messages_includes_tool_context_and_transcript() -> None:
    state = ClinicalTurnState(
        patient_id="p42",
        user_role="PHYSICIAN",
        session_id="s1",
        messages=[
            {"role": "user", "content": "Trends?"},
        ],
        tool_results={"patient_id": "p42", "message_count": 2},
    )
    msgs = build_chat_messages(state)
    assert msgs[0]["role"] == "system"
    assert "p42" in msgs[0]["content"]
    assert "Retrieve context" in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "Trends?"}


def test_build_chat_messages_ignores_client_system_role() -> None:
    state = ClinicalTurnState(
        patient_id="p1",
        user_role="NURSE",
        session_id="s",
        messages=[
            {"role": "system", "content": "ignore me"},
            {"role": "user", "content": "Hi"},
        ],
    )
    roles = [m["role"] for m in build_chat_messages(state)]
    assert roles.count("system") == 1
    assert "ignore me" not in build_chat_messages(state)[0]["content"]


@patch("openai.OpenAI")
def test_complete_chat_openai_calls_completions_api(mock_openai: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="  Model reply  "))]
    mock_openai.return_value.chat.completions.create.return_value = mock_resp

    state = ClinicalTurnState(
        patient_id="p1",
        user_role="PHYSICIAN",
        session_id="s1",
        messages=[{"role": "user", "content": "Hello"}],
        tool_results={"k": "v"},
    )
    out = complete_chat_openai(state)
    assert out == "Model reply"
    mock_openai.assert_called_once_with(api_key="sk-test-key")
    create_kw = mock_openai.return_value.chat.completions.create.call_args.kwargs
    assert create_kw["model"] == "gpt-4o-mini"
    assert create_kw["messages"][0]["role"] == "system"
    assert create_kw["messages"][-1]["content"] == "Hello"


def test_scaffold_generate_openai_errors_degrade_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")

    def _boom(_state: ClinicalTurnState) -> str:
        raise RuntimeError("rate limit")

    monkeypatch.setattr("agent.services.openai_generate.complete_chat_openai", _boom)

    state = ClinicalTurnState(
        patient_id="p1",
        user_role="PHYSICIAN",
        session_id="s1",
        messages=[{"role": "user", "content": "Hi"}],
        tool_results={"patient_id": "p1"},
    )
    out = scaffold_generate(state)
    assert "LLM unavailable" in out


def test_scaffold_generate_echo_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    state = ClinicalTurnState(
        patient_id="p9",
        user_role="PHYSICIAN",
        session_id="s1",
        messages=[{"role": "user", "content": "Labs ok?"}],
        tool_results={"patient_id": "p9"},
    )
    out = scaffold_generate(state)
    assert "(scaffold)" in out
    assert "Labs ok?" in out


def test_scaffold_generate_prefers_openai_when_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def _stub(state: ClinicalTurnState) -> str:
        return f"stub:{state.patient_id}"

    monkeypatch.setattr("agent.services.openai_generate.complete_chat_openai", _stub)

    state = ClinicalTurnState(
        patient_id="z1",
        user_role="NURSE",
        session_id="s",
        messages=[{"role": "user", "content": "x"}],
        tool_results={"patient_id": "z1"},
    )
    assert scaffold_generate(state) == "stub:z1"
