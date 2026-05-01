"""
Scaffold conversational turn: append user message → RGV pipeline → append assistant.

Replace retrieve/generate/verify callables with LangGraph + LLM + grounding in the fork.
"""

from __future__ import annotations

import logging
import uuid

from agent.observability.events import log_agent_event
from agent.runtime.rgv_pipeline import ClinicalTurnState, run_retrieve_generate_verify

_LOG = logging.getLogger(__name__)


def scaffold_retrieve(state: ClinicalTurnState) -> dict[str, object]:
    """Placeholder tool aggregation (no live FHIR in this repo)."""
    return {
        "patient_id": state.patient_id,
        "user_role": state.user_role,
        "message_count": len(state.messages),
    }


def scaffold_generate(state: ClinicalTurnState) -> str:
    """Placeholder LLM: echo last user turn + tool summary."""
    last_user = ""
    for m in reversed(state.messages):
        if m.get("role") == "user":
            last_user = str(m.get("content", ""))
            break
    ctx = state.tool_results.get("patient_id", "?")
    return f"(scaffold) Context for patient {ctx}: {last_user}"


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
        verify=scaffold_verify,
    )
    st.messages.append({"role": "assistant", "content": assistant})
    log_agent_event(
        _LOG,
        "chat_turn_complete",
        verified=st.verified,
        verify_retry_count=st.verify_retry_count,
        patient_id=st.patient_id,
        session_id=st.session_id,
    )
    return st, assistant


def new_session_id() -> str:
    return str(uuid.uuid4())
