"""
Phase 5: repeatable latency sampling (gated — keeps default CI fast).

Set ``RUN_LATENCY_GATE=1`` and optionally ``AGENT_LATENCY_GATE_MS`` (default 3000)
for a coarse upper bound on scaffold ``POST /agent/chat`` wall time via TestClient.
This is not a substitute for production SLO measurement.
"""

from __future__ import annotations

import os
import time
from typing import Annotated

import pytest
from fastapi import Header, Request
from fastapi.testclient import TestClient

from agent.http.app import create_app
from agent.http.deps import resolve_agent_role


def _fake_physician(
    _request: Request,
    _authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    _cookie: Annotated[str | None, Header(alias="Cookie")] = None,
) -> str:
    return "PHYSICIAN"


@pytest.mark.skipif(
    not os.environ.get("RUN_LATENCY_GATE"),
    reason="set RUN_LATENCY_GATE=1 to run coarse chat latency sampling",
)
def test_scaffold_chat_turn_max_wall_under_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.test")
    gate_ms = float(os.environ.get("AGENT_LATENCY_GATE_MS", "3000"))
    app = create_app()
    app.dependency_overrides[resolve_agent_role] = _fake_physician
    samples: list[float] = []
    with TestClient(app) as client:
        for _ in range(15):
            t0 = time.perf_counter()
            r = client.post(
                "/agent/chat",
                json={
                    "patient_id": "p-latency",
                    "user_message": "latency probe",
                    "messages": [],
                },
                headers={"Authorization": "Bearer probe"},
            )
            samples.append((time.perf_counter() - t0) * 1000.0)
            assert r.status_code == 200, r.text
    worst = max(samples)
    assert worst < gate_ms, (
        f"max sample {worst:.1f}ms >= gate {gate_ms}ms — adjust model/env or gate for CI hardware"
    )
