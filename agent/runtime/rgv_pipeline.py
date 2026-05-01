"""
Minimal retrieve → generate → verify loop with bounded retry (ARCHITECTURE.md).

This is a scaffold for LangGraph: same ordering and retry cap, without graph framework deps.
Integrate with real tool dispatch + LLM in the OpenEMR fork.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# ARCHITECTURE: verify failure → retry ≤ 1 (one retry → at most two generate passes).
MAX_VERIFY_RETRIES: int = 1


@dataclass
class ClinicalTurnState:
    """Per-turn state (subset of AgentState from architecture narrative)."""

    patient_id: str
    user_role: str
    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_results: dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    verify_retry_count: int = 0
    verification_notes: list[str] = field(default_factory=list)


RetrieveFn = Callable[[ClinicalTurnState], dict[str, Any]]
GenerateFn = Callable[[ClinicalTurnState], str]
VerifyFn = Callable[[ClinicalTurnState, str], tuple[bool, str]]


def run_retrieve_generate_verify(
    state: ClinicalTurnState,
    *,
    retrieve: RetrieveFn,
    generate: GenerateFn,
    verify: VerifyFn,
) -> tuple[ClinicalTurnState, str]:
    """
    Run retrieve once, then generate → verify with at most MAX_VERIFY_RETRIES re-generations.

    On persistent verify failure after retries exhausted, returns last model text with
    ``state.verified`` False (graceful degradation — caller must not treat as medically verified).
    """
    state.tool_results = dict(retrieve(state))
    state.verified = False
    state.verify_retry_count = 0
    state.verification_notes.clear()

    last_text = ""
    while True:
        last_text = generate(state)
        ok, note = verify(state, last_text)
        if note:
            state.verification_notes.append(note)
        if ok:
            state.verified = True
            return state, last_text
        if state.verify_retry_count >= MAX_VERIFY_RETRIES:
            state.verified = False
            return state, last_text
        state.verify_retry_count += 1
