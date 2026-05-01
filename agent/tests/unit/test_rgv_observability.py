"""RGV pipeline emits Phase 4 structured events on verify failure / degradation."""

from __future__ import annotations

import logging

import pytest

from agent.observability.events import LOG_EXTRA_EVENT
from agent.observability.taxonomy import RGV_DEGRADED_UNVERIFIED, RGV_VERIFY_RETRY, VERIFY_FAILURE
from agent.runtime.rgv_pipeline import MAX_VERIFY_RETRIES, ClinicalTurnState, run_retrieve_generate_verify


def _state() -> ClinicalTurnState:
    return ClinicalTurnState(patient_id="p1", user_role="PHYSICIAN", session_id="s1")


def test_verify_fail_then_retry_emits_events(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    gen_calls = 0

    def retrieve(_s: ClinicalTurnState) -> dict:
        return {}

    def generate(_s: ClinicalTurnState) -> str:
        nonlocal gen_calls
        gen_calls += 1
        return f"v{gen_calls}"

    def verify(_s: ClinicalTurnState, text: str) -> tuple[bool, str]:
        if text == "v2":
            return True, "ok"
        return False, "first_fail"

    st, out = run_retrieve_generate_verify(_state(), retrieve=retrieve, generate=generate, verify=verify)
    assert out == "v2"
    assert st.verified is True
    types = [getattr(r, LOG_EXTRA_EVENT) for r in caplog.records if r.name == "agent.runtime.rgv_pipeline"]
    assert VERIFY_FAILURE in types
    assert RGV_VERIFY_RETRY in types
    assert RGV_DEGRADED_UNVERIFIED not in types


def test_verify_always_fails_emits_degraded(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    def retrieve(_s: ClinicalTurnState) -> dict:
        return {}

    def generate(_s: ClinicalTurnState) -> str:
        return "bad"

    def verify(_s: ClinicalTurnState, _t: str) -> tuple[bool, str]:
        return False, "fail"

    st, _ = run_retrieve_generate_verify(_state(), retrieve=retrieve, generate=generate, verify=verify)
    assert st.verified is False
    assert st.verify_retry_count == MAX_VERIFY_RETRIES
    types = [getattr(r, LOG_EXTRA_EVENT) for r in caplog.records if r.name == "agent.runtime.rgv_pipeline"]
    assert VERIFY_FAILURE in types
    assert RGV_VERIFY_RETRY in types
    assert RGV_DEGRADED_UNVERIFIED in types
