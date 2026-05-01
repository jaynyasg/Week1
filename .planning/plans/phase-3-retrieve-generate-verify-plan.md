# Phase 3 Execution Plan — Retrieve → Generate → Verify

## Objective
Ship the clinical agent core loop: **retrieve patient context → generate model output → verify** with **bounded retry** and **multi-turn state**, aligned with `ARCHITECTURE.md` and PRD agent requirements.

## Non-Goals
- Full LangGraph migration in this scaffold repo (optional follow-up in fork).
- New observability backends (Phase 4).
- Latency benchmarking gates (Phase 5).

## Current Scaffold (Week1 repo)
- `agent/runtime/rgv_pipeline.py` — pure-Python loop with `MAX_VERIFY_RETRIES = 1`.
- `agent/services/chat_turn.py` — scaffold retrieve/generate/verify wired to the pipeline; `POST /agent/chat` in `agent/http/app.py`.
- Unit tests: `agent/tests/unit/test_rgv_pipeline.py`, `agent/tests/unit/test_chat_turn.py`.
- Integration tests: `agent/tests/integration/test_chat_route.py` (happy path, multi-turn, missing `Authorization` → 401), `test_tool_route_rbac.py`; optional live checks in `test_live_openemr_optional.py` (`RUN_LIVE_OPENEMR_E2E=1`, token vars per `.env.example`; `RUN_LIVE_OPENEMR_TESTS=1` alias).
- Items 4–5 under **Work Breakdown** are partially satisfied in-repo; fork work completes real retrieve/LLM/verify and closes `REQ-agent-requirements-coverage`.

## Work Breakdown (fork / full agent)
1. **Replace stub callables** with real retrieve node (tools + RBAC already from Phase 2).
2. **Wire generate** to LLM with streaming adapter; preserve `ClinicalTurnState.messages`.
3. **Implement verify** — grounding + domain rules modules; emit verification-limit notes on partial failure.
4. **Map HTTP/chat** endpoint to pipeline entry; ensure session + `patient_id` scoping on each turn.
5. **Tests** — integration tests for retry boundary, verify-fail degradation, multi-turn message continuity.

## Exit Criteria (requirement IDs)
| ID | Done when |
|----|-------------|
| `REQ-retrieve-generate-verify-loop` | Retrieve runs before first generate; verify gates response; ≤1 verify retry; non-verified exit is explicit. |
| `REQ-multi-turn-usecase-behavior` | State carries messages + role/session across successive pipeline invocations. |
| `REQ-verification-layer-contracts` | Verify returns structured pass/fail + notes; no silent success on verify failure. |
| `REQ-agent-requirements-coverage` | PRD agent surfaces reflected in runnable path (chat + tools + verify). |

## Suggested Order
1. Tool-backed retrieve + RBAC (reuse Phase 2).
2. Verify module + unit tests.
3. LLM generate + streaming.
4. E2E chat integration tests.
