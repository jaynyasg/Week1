"""Scaffold chat turn (retrieve → generate → verify)."""

from __future__ import annotations

from agent.services.chat_turn import run_scaffold_chat_turn


def test_scaffold_chat_happy_path() -> None:
    st, out = run_scaffold_chat_turn(
        patient_id="pat-1",
        user_role="PHYSICIAN",
        session_id="sess-1",
        messages=[],
        user_message="Any concerns before rounds?",
    )
    assert st.verified is True
    assert "Any concerns" in out
    assert st.messages[-1]["role"] == "assistant"
    assert len(st.verification_notes) >= 1


def test_scaffold_verify_fail_then_retry() -> None:
    st, out = run_scaffold_chat_turn(
        patient_id="pat-1",
        user_role="PHYSICIAN",
        session_id="sess-1",
        messages=[],
        user_message="Check labs [[VERIFY_FAIL]]",
    )
    assert st.verified is True
    assert st.verify_retry_count == 1
    assert any("recovered" in n.lower() for n in st.verification_notes)
