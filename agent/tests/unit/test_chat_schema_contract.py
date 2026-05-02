"""Chat request/response schema invariants (API contract)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.http.schemas import ChatRequest, ChatResponse


def test_chat_request_rejects_oversized_history() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            patient_id="p",
            user_message="hi",
            messages=[{"role": "user", "content": str(i)} for i in range(501)],
        )


def test_chat_response_required_keys_roundtrip() -> None:
    payload = {
        "assistant_message": "ok",
        "verified": True,
        "verification_notes": ["n1"],
        "verify_retry_count": 0,
        "tool_result_keys": ["patient_id"],
        "messages": [{"role": "user", "content": "x"}],
    }
    m = ChatResponse.model_validate(payload)
    dumped = m.model_dump(exclude_none=True)
    assert set(dumped.keys()) == {
        "assistant_message",
        "verified",
        "verification_notes",
        "verify_retry_count",
        "tool_result_keys",
        "messages",
    }
    full = m.model_dump()
    assert full.get("tool_execution_summary") is None


def test_chat_response_optional_tool_execution_summary() -> None:
    m = ChatResponse(
        assistant_message="a",
        verified=True,
        verification_notes=[],
        verify_retry_count=0,
        tool_result_keys=["k"],
        tool_execution_summary=[{"function": "get_patient_demographics", "status": "ok"}],
        messages=[{"role": "user", "content": "x"}],
    )
    d = m.model_dump(exclude_none=True)
    assert d["tool_execution_summary"] == [
        {"function": "get_patient_demographics", "status": "ok"}
    ]
