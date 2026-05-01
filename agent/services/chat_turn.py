"""
Scaffold conversational turn: append user message → RGV pipeline → append assistant.

Replace retrieve/generate/verify callables with LangGraph + LLM + grounding in the fork.
"""

from __future__ import annotations

import logging
import os
import uuid

from agent.observability.events import log_agent_event
from agent.observability.taxonomy import CATEGORY_BOUNDARY_REVIEW, CHAT_TURN_COMPLETE
from agent.runtime.rgv_pipeline import ClinicalTurnState, VerifyFn, run_retrieve_generate_verify

_LOG = logging.getLogger(__name__)


def scaffold_retrieve(state: ClinicalTurnState) -> dict[str, object]:
    """Placeholder tool aggregation (no live FHIR in this repo)."""
    out: dict[str, object] = {
        "patient_id": state.patient_id,
        "user_role": state.user_role,
        "message_count": len(state.messages),
    }
    # Synthetic dual-category context for observability tests (labs vs vitals boundary flag).
    last_user = ""
    for m in reversed(state.messages):
        if m.get("role") == "user":
            last_user = str(m.get("content", ""))
            break
    if "dual_category_demo" in last_user:
        out["labs_context"] = "synthetic"
        out["vitals_context"] = "synthetic"
    return out


def _scaffold_generate_echo(state: ClinicalTurnState) -> str:
    """Offline / CI placeholder when ``OPENAI_API_KEY`` is unset."""
    last_user = ""
    for m in reversed(state.messages):
        if m.get("role") == "user":
            last_user = str(m.get("content", ""))
            break
    ctx = state.tool_results.get("patient_id", "?")
    return f"(scaffold) Context for patient {ctx}: {last_user}"


def scaffold_generate(state: ClinicalTurnState) -> str:
    """
    LLM-backed reply when ``OPENAI_API_KEY`` is set (e.g. Fly secret); otherwise echo scaffold.

    On transient model errors, returns a short parenthetical so the HTTP layer can still 200;
    operators should watch logs for stack traces.
    """
    if os.environ.get("OPENAI_API_KEY", "").strip():
        try:
            from agent.services.openai_generate import complete_chat_openai

            return complete_chat_openai(state)
        except Exception:
            _LOG.exception("openai_generate_failed")
            return "(LLM unavailable; check logs and OPENAI_API_KEY / model access.)"
    return _scaffold_generate_echo(state)


def scaffold_verify(state: ClinicalTurnState, text: str) -> tuple[bool, str]:
    """
    Placeholder verification: pass when tool bundle present.

    Use ``[[VERIFY_FAIL]]`` in the user message to exercise the bounded retry path:
    first verify pass fails; after pipeline increment, second pass succeeds.
    """
    last_user = ""
    for m in reversed(state.messages):
        if m.get("role") == "user":
            last_user = str(m.get("content", ""))
            break
    if "[[VERIFY_FAIL]]" in last_user:
        if state.verify_retry_count >= 1:
            return True, "recovered after bounded retry"
        return False, "simulated verify failure (first pass)"
    if not state.tool_results:
        return False, "missing tool results"
    return True, "scaffold verify ok"


def run_scaffold_chat_turn(
    *,
    patient_id: str,
    user_role: str,
    session_id: str,
    messages: list[dict[str, object]],
    user_message: str,
    verify: VerifyFn | None = None,
) -> tuple[ClinicalTurnState, str]:
    state = ClinicalTurnState(
        patient_id=patient_id,
        user_role=user_role,
        session_id=session_id,
        messages=list(messages),
    )
    state.messages.append({"role": "user", "content": user_message})
    st, assistant = run_retrieve_generate_verify(
        state,
        retrieve=scaffold_retrieve,
        generate=scaffold_generate,
        verify=verify or scaffold_verify,
    )
    st.messages.append({"role": "assistant", "content": assistant})
    if st.tool_results.get("labs_context") and st.tool_results.get("vitals_context"):
        log_agent_event(
            _LOG,
            CATEGORY_BOUNDARY_REVIEW,
            what="labs_and_vitals_context_same_turn",
            why="synthetic_scaffold_signal",
            duration_ms=st.rgv_duration_ms,
            fallback="human_review_recommended",
            cost_envelope="unknown",
        )
    log_agent_event(
        _LOG,
        CHAT_TURN_COMPLETE,
        verified=st.verified,
        verify_retry_count=st.verify_retry_count,
        patient_id=st.patient_id,
        session_id=st.session_id,
        rgv_duration_ms=st.rgv_duration_ms,
        fallback="none" if st.verified else "unverified_response",
        cost_envelope="unknown",
    )
    return st, assistant


def new_session_id() -> str:
    return str(uuid.uuid4())
