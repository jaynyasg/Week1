"""Optional live OpenAI smoke (requires ``OPENAI_API_KEY`` in the environment)."""

from __future__ import annotations

import os

import pytest

from agent.services.chat_turn import run_scaffold_chat_turn


@pytest.mark.skipif(
    not (os.environ.get("OPENAI_API_KEY") or "").strip(),
    reason="OPENAI_API_KEY not set — skipping live LLM integration",
)
def test_live_openai_scaffold_turn() -> None:
    st, assistant = run_scaffold_chat_turn(
        patient_id="demo-patient",
        user_role="PHYSICIAN",
        session_id="live-openai-test",
        messages=[],
        user_message='Reply with exactly the word "pong" and nothing else.',
    )
    assert st.verified is True
    assert "pong" in assistant.lower()
