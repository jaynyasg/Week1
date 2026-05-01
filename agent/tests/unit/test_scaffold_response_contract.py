"""Phase 3 scaffold: HTTP response field invariants aligned with ROADMAP SC3 (contract-only)."""

from __future__ import annotations

from agent.http.schemas import ChatResponse
from agent.runtime.rgv_pipeline import MAX_VERIFY_RETRIES, ClinicalTurnState
from agent.services.chat_turn import run_scaffold_chat_turn, scaffold_verify


def _as_chat_response(st: ClinicalTurnState, assistant: str) -> ChatResponse:
    """Mirror ``routes_chat.chat_turn`` mapping (keeps contract tests aligned with HTTP)."""
    return ChatResponse(
        assistant_message=assistant,
        verified=st.verified,
        verification_notes=list(st.verification_notes),
        verify_retry_count=st.verify_retry_count,
        tool_result_keys=sorted(st.tool_results.keys()),
        messages=st.messages,
    )


def test_happy_path_response_sorted_tool_keys_and_transcript() -> None:
    st, assistant = run_scaffold_chat_turn(
        patient_id="p1",
        user_role="PHYSICIAN",
        session_id="s1",
        messages=[],
        user_message="rounds question",
    )
    resp = _as_chat_response(st, assistant)
    assert resp.tool_result_keys == sorted(resp.tool_result_keys)
    assert "message_count" in resp.tool_result_keys
    assert resp.messages[-1]["role"] == "assistant"
    assert resp.messages[-2]["role"] == "user"
    assert resp.verified is True
    assert resp.verify_retry_count == 0


def test_degraded_unverified_exposes_notes_and_retry_budget() -> None:
    def always_fail(_state: object, _text: str) -> tuple[bool, str]:
        return False, "scaffold domain check failed"

    st, assistant = run_scaffold_chat_turn(
        patient_id="p1",
        user_role="PHYSICIAN",
        session_id="s1",
        messages=[],
        user_message="needs verification",
        verify=always_fail,
    )
    resp = _as_chat_response(st, assistant)
    assert resp.verified is False
    assert resp.verify_retry_count == MAX_VERIFY_RETRIES
    assert len(resp.verification_notes) >= 1
    assert any(
        "failed" in n.lower() or "false" in n.lower() for n in resp.verification_notes
    )
    assert (
        assistant
    )  # still returns last model text; operator must not treat as verified


def test_dual_category_user_message_sets_both_tool_keys() -> None:
    st, assistant = run_scaffold_chat_turn(
        patient_id="p1",
        user_role="PHYSICIAN",
        session_id="s1",
        messages=[],
        user_message="dual_category_demo labs and vitals",
        verify=scaffold_verify,
    )
    resp = _as_chat_response(st, assistant)
    assert "labs_context" in resp.tool_result_keys
    assert "vitals_context" in resp.tool_result_keys
