"""
Minimal retrieve → generate → verify loop with bounded retry (ARCHITECTURE.md).

This is a scaffold for LangGraph: same ordering and retry cap, without graph framework deps.
Integrate with real tool dispatch + LLM in the OpenEMR fork.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from agent.observability.events import log_agent_event
from agent.observability.taxonomy import (
    RGV_DEGRADED_UNVERIFIED,
    RGV_VERIFY_RETRY,
    VERIFY_FAILURE,
)

_LOG = logging.getLogger(__name__)

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
    rgv_duration_ms: float = 0.0


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
    t0 = time.monotonic()
    try:
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
            log_agent_event(
                _LOG,
                VERIFY_FAILURE,
                what="verification_rejected",
                why=(note[:240] if note else "verify_returned_false"),
                verify_retry_count=state.verify_retry_count,
                duration_ms=round((time.monotonic() - t0) * 1000, 3),
                fallback="retry_generate" if state.verify_retry_count < MAX_VERIFY_RETRIES else "return_unverified",
                cost_envelope="unknown",
            )
            if state.verify_retry_count >= MAX_VERIFY_RETRIES:
                state.verified = False
                log_agent_event(
                    _LOG,
                    RGV_DEGRADED_UNVERIFIED,
                    what="verification_exhausted",
                    why=(note[:240] if note else "verify_still_false"),
                    verify_retry_count=state.verify_retry_count,
                    duration_ms=round((time.monotonic() - t0) * 1000, 3),
                    fallback="return_unverified",
                    cost_envelope="unknown",
                )
                return state, last_text
            log_agent_event(
                _LOG,
                RGV_VERIFY_RETRY,
                what="bounded_regenerate",
                why="verify_failed_within_retry_budget",
                next_verify_retry_count=state.verify_retry_count + 1,
                duration_ms=round((time.monotonic() - t0) * 1000, 3),
                fallback="regenerate_once",
                cost_envelope="unknown",
            )
            state.verify_retry_count += 1
    finally:
        state.rgv_duration_ms = round((time.monotonic() - t0) * 1000, 3)
