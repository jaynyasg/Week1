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

## Gap table — ROADMAP success criteria vs repo (2026-04-30)

Maps [Phase 3 success criteria in ROADMAP](../ROADMAP.md) and exit IDs above to **concrete artifacts**. Phase 3 stays **in progress** until fork closes rows marked **Gap**.

| Criterion / ID | Concrete repo artifacts (evidence) | Status | Fork / stack owner |
|---|---|---|---|
| SC1 — retrieve → generate → verify order | `agent/runtime/rgv_pipeline.py` (`run_retrieve_generate_verify`), `agent/services/chat_turn.py`, `agent/http/app.py` `POST /agent/chat`, `agent/http/deps.py` `get_chat_turn_runner` → `run_scaffold_chat_turn`, `agent/tests/unit/test_rgv_pipeline.py::test_retrieve_runs_before_generate` | **Met** | — |
| SC2 — multi-turn session/role | Same chat route; `test_chat_route.py::test_chat_multiturn_carries_history`; `Header` `X-Clinical-Session-Id`; role from `resolve_agent_role` (live OpenEMR or test override) | **Met (contract)** | Clinical state depth → fork |
| SC3 — domain constraints + source attribution + limit notes | `agent/http/schemas.py` `ChatResponse` (`verification_notes`, `verified`, `tool_result_keys`); **no** dedicated source-attribution payload; `scaffold_verify` / `scaffold_generate` are placeholders | **Gap** | OpenEMR fork |
| SC4 — architecture maps chatbot / verify / observability / eval | `.planning/AI-ARCHITECTURE.md` § PRD Agent Requirements Coverage (1–4) | **Met (documentation)** | Executable parity → fork |
| SC5 — bounded deterministic retry | `MAX_VERIFY_RETRIES` in `rgv_pipeline.py`; `test_verify_retry_at_most_once_then_degrade`, `test_verify_always_fails_degrades_without_infinite_loop` | **Met** | — |
| SC6 — graceful degradation | `test_chat_route.py::test_chat_graceful_degradation_verified_false_after_retries`; pipeline docstring on `verified=False` | **Met** | — |
| Live E2E gate (OpenEMR / agent) | `agent/tests/integration/test_live_openemr_optional.py` (`RUN_LIVE_OPENEMR_E2E`, env per `.env.example`) | **Present (opt-in)** | Operators with secrets |
| Observability on chat turn | `agent/services/chat_turn.py` `log_agent_event(..., "chat_turn_complete", ...)`, `agent/tests/integration/test_http_logging_observability.py` | **Met (log contract)** | Full Phase 4 operator questions → later phase |
| `REQ-retrieve-generate-verify-loop` | Same as SC1 + retry/degrade tests | **Met (scaffold)** | Real EMR retrieve + verify |
| `REQ-multi-turn-usecase-behavior` | Same as SC2 | **Met (scaffold)** | Fork |
| `REQ-verification-layer-contracts` | Verify tuple + notes list; forced-fail HTTP test | **Met (contract)** | Domain rules → fork |
| `REQ-agent-requirements-coverage` | No LangGraph/LLM/FHIR-backed runnable path in Week1 | **Gap** | **OpenEMR fork** |

**Decision:** Do **not** mark ROADMAP Phase 3 complete: **SC3** (real domain + source attribution) and **`REQ-agent-requirements-coverage`** are honest blockers for closure in this repo. `.planning/AI-ARCHITECTURE.md` requirement traceability may show design satisfaction; runtime PRD coverage remains fork-owned.

### Schedule guidance (fork)

| Surface | What stays / completes here |
|--------|-----------------------------|
| **This repo (Week1)** | Scaffold: RGV ordering, bounded retry, multi-turn HTTP + session headers, verify **contract** (structured pass/fail + notes), tests and optional live OpenEMR hooks — matches Gap rows already **Met** / **Met (scaffold)** / **Met (contract)**. |
| **Fork / deployed stack** | Real EMR-backed retrieve, production LLM generate, domain verify + **record-backed source attribution** (SC3), runnable PRD path for **`REQ-agent-requirements-coverage`** — same rows as **Gap** / **OpenEMR fork** in the table above and in [ROADMAP Phase 3 gap table](../ROADMAP.md). Phase 3 stays **in progress** in the progress table until fork/runtime clears those gaps. |

**Week-range estimates (order-of-magnitude; not commitments):**

- **Thin MVP (~2–4 weeks):** Assumes Phase 2 RBAC/tools reused as-is, one primary clinical use-case, single LLM provider, thin verify rules, no LangGraph migration. Goal: end-to-end chat with real retrieve + generate + verify sufficient to start closing **`REQ-agent-requirements-coverage`** under staged/CI evidence; SC3 attribution may be minimal (e.g., tool refs) with follow-up polish.
- **Broader agent (~6–10 weeks):** Assumes multiple flows, richer session/clinical state, fuller grounding + domain verify modules, streaming hardening, optional graph orchestration, and SC3 closer to full response-artifact parity (attribution + verification-limit notes aligned with PRD).

Downstream work stays ROADMAP-sequenced after Phase 3 closure: [Phase 4 — Observability](./phase-4-observability-plan.md) (operator-question telemetry, safety flagging) depends on Phase 3; [Phase 5 — Evaluation](./phase-5-evaluation-plan.md) (latency, RBAC eval breadth, cost gates) depends on Phase 4. Trace **`REQ-agent-requirements-coverage`** to the Exit Criteria table and the Gap table row **`REQ-agent-requirements-coverage` → OpenEMR fork**.

## Suggested Order
1. Tool-backed retrieve + RBAC (reuse Phase 2).
2. Verify module + unit tests.
3. LLM generate + streaming.
4. E2E chat integration tests.
