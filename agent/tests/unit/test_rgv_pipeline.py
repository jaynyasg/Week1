"""Retrieve → generate → verify scaffold (bounded retry)."""

from __future__ import annotations

import pytest

from agent.runtime.rgv_pipeline import (
    MAX_VERIFY_RETRIES,
    ClinicalTurnState,
    run_retrieve_generate_verify,
)


def _base_state() -> ClinicalTurnState:
    return ClinicalTurnState(
        patient_id="p1",
        user_role="PHYSICIAN",
        session_id="s1",
    )


def test_retrieve_exception_propagates() -> None:
    def retrieve(_s: ClinicalTurnState) -> dict:
        raise RuntimeError("retrieve boom")

    def generate(_s: ClinicalTurnState) -> str:
        return "never"

    def verify(_s: ClinicalTurnState, _t: str) -> tuple[bool, str]:
        return True, ""

    with pytest.raises(RuntimeError, match="retrieve boom"):
        run_retrieve_generate_verify(
            _base_state(), retrieve=retrieve, generate=generate, verify=verify
        )


def test_retrieve_runs_before_generate() -> None:
    order: list[str] = []

    def retrieve(s: ClinicalTurnState) -> dict:
        order.append("retrieve")
        return {"x": 1}

    def generate(s: ClinicalTurnState) -> str:
        order.append("generate")
        assert s.tool_results.get("x") == 1
        return "ok"

    def verify(_s: ClinicalTurnState, text: str) -> tuple[bool, str]:
        order.append("verify")
        return True, ""

    st, out = run_retrieve_generate_verify(
        _base_state(), retrieve=retrieve, generate=generate, verify=verify
    )
    assert out == "ok"
    assert st.verified is True
    assert order == ["retrieve", "generate", "verify"]


def test_verify_retry_at_most_once_then_degrade() -> None:
    gen_calls = 0

    def retrieve(s: ClinicalTurnState) -> dict:
        return {}

    def generate(s: ClinicalTurnState) -> str:
        nonlocal gen_calls
        gen_calls += 1
        return f"v{gen_calls}"

    def verify(_s: ClinicalTurnState, text: str) -> tuple[bool, str]:
        if text == "v2":
            return True, "recovered"
        return False, "not yet"

    st, out = run_retrieve_generate_verify(
        _base_state(), retrieve=retrieve, generate=generate, verify=verify
    )
    assert gen_calls == 2
    assert out == "v2"
    assert st.verified is True
    assert st.verify_retry_count == 1
    assert "recovered" in st.verification_notes


def test_empty_tool_results_verify_fails_and_degrades_with_notes() -> None:
    """Retrieve may yield {} — verify should fail explicitly (scaffold-style contract)."""

    def retrieve(_s: ClinicalTurnState) -> dict:
        return {}

    def generate(_s: ClinicalTurnState) -> str:
        return "suggestion"

    def verify(s: ClinicalTurnState, _t: str) -> tuple[bool, str]:
        if not s.tool_results:
            return False, "missing tool results"
        return True, "ok"

    st, out = run_retrieve_generate_verify(
        _base_state(), retrieve=retrieve, generate=generate, verify=verify
    )
    assert st.verified is False
    assert out == "suggestion"
    assert st.verify_retry_count == 1
    joined = " ".join(st.verification_notes).lower()
    assert "missing" in joined


def test_verify_always_fails_degrades_without_infinite_loop() -> None:
    gen_calls = 0

    def retrieve(_s: ClinicalTurnState) -> dict:
        return {}

    def generate(_s: ClinicalTurnState) -> str:
        nonlocal gen_calls
        gen_calls += 1
        return "bad"

    def verify(_s: ClinicalTurnState, _text: str) -> tuple[bool, str]:
        return False, "fail"

    st, out = run_retrieve_generate_verify(
        _base_state(), retrieve=retrieve, generate=generate, verify=verify
    )
    assert gen_calls == MAX_VERIFY_RETRIES + 1
    assert out == "bad"
    assert st.verified is False
    assert st.verify_retry_count == MAX_VERIFY_RETRIES


def test_multi_turn_preserves_messages_across_calls() -> None:
    st = _base_state()
    st.messages.append({"role": "user", "content": "first"})

    def r1(s: ClinicalTurnState) -> dict:
        assert len(s.messages) == 1
        return {}

    def g1(s: ClinicalTurnState) -> str:
        s.messages.append({"role": "assistant", "content": "a1"})
        return "a1"

    def v1(_s: ClinicalTurnState, _t: str) -> tuple[bool, str]:
        return True, ""

    st, _ = run_retrieve_generate_verify(st, retrieve=r1, generate=g1, verify=v1)
    st.messages.append({"role": "user", "content": "second"})

    def r2(s: ClinicalTurnState) -> dict:
        assert any(m.get("content") == "second" for m in s.messages)
        return {}

    def g2(s: ClinicalTurnState) -> str:
        s.messages.append({"role": "assistant", "content": "a2"})
        return "a2"

    def v2(_s: ClinicalTurnState, _t: str) -> tuple[bool, str]:
        return True, ""

    st, out = run_retrieve_generate_verify(st, retrieve=r2, generate=g2, verify=v2)
    assert out == "a2"
    assert len(st.messages) == 4
