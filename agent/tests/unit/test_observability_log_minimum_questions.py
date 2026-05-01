"""NFR-observability-minimum-questions: structured log records carry triage fields."""

from __future__ import annotations

import logging

import pytest

from agent.access.rbac import log_tool_refusal
from agent.observability.events import LOG_EXTRA_EVENT_TYPE
from agent.observability.taxonomy import VERIFY_FAILURE
from agent.runtime.rgv_pipeline import ClinicalTurnState, run_retrieve_generate_verify


@pytest.fixture
def caplog_structured(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.INFO)
    return caplog


def test_log_tool_refusal_includes_minimum_operator_fields(
    caplog_structured: pytest.LogCaptureFixture,
) -> None:
    log = logging.getLogger("agent.tests.rbac_refusal_contract")
    log_tool_refusal(log, "NURSE", "labs")
    assert len(caplog_structured.records) == 1
    r = caplog_structured.records[0]
    assert getattr(r, LOG_EXTRA_EVENT_TYPE) == "tool_refusal"
    assert getattr(r, "what") == "rbac_tool_denied"
    assert getattr(r, "why") == "role_tool_matrix"
    assert getattr(r, "duration_ms") == 0.0
    assert getattr(r, "fallback") == "none"
    assert getattr(r, "cost_envelope") == "unknown"


def test_rgv_verify_failure_log_includes_minimum_operator_fields(
    caplog_structured: pytest.LogCaptureFixture,
) -> None:
    # Capture INFO from the RGV module (and parents) for structured agent_event lines.
    caplog_structured.set_level(logging.INFO)

    def retrieve(_s: ClinicalTurnState) -> dict:
        return {"ok": 1}

    def generate(_s: ClinicalTurnState) -> str:
        return "draft"

    def verify(_s: ClinicalTurnState, _t: str) -> tuple[bool, str]:
        return False, "domain rule failed"

    st, text = run_retrieve_generate_verify(
        ClinicalTurnState(
            patient_id="p",
            user_role="PHYSICIAN",
            session_id="s",
        ),
        retrieve=retrieve,
        generate=generate,
        verify=verify,
    )
    assert st.verified is False
    assert text == "draft"
    failure_logs = [
        r
        for r in caplog_structured.records
        if getattr(r, LOG_EXTRA_EVENT_TYPE, None) == VERIFY_FAILURE
    ]
    assert failure_logs, "expected at least one verify_failure structured log"
    r = failure_logs[0]
    assert getattr(r, "what") == "verification_rejected"
    assert "domain" in str(getattr(r, "why", "")).lower()
    assert getattr(r, "fallback") in ("retry_generate", "return_unverified")
    assert getattr(r, "cost_envelope") == "unknown"
    assert isinstance(getattr(r, "duration_ms", None), float)
