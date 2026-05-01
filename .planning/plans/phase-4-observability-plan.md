# Phase 4 Execution Plan — Observability and Clinical Safety Flagging

## Objective
Make **RBAC denials**, **verification failures**, **fallbacks**, and **category-boundary risks** visible through **structured, queryable telemetry** so operators can triage without raw internals—building on the existing event helper.

## Non-Goals
- Langfuse or other backend provisioning as a hard dependency (optional follow-on).
- Phase 5 latency/cost evaluation harnesses and release gates.
- Changing RBAC policy matrix (Phase 2); this phase **observes** boundary integrity.

## Current Baseline (Week1 repo)
- `agent/observability/events.py` — `log_agent_event()` emits structured `agent_event` log lines with `extra={"event_type", ...}` for downstream collectors; documented as the hook for future Langfuse (Phase 4).

## Work Items
1. **Event taxonomy** — Define stable `event_type` values and required/optional fields for denials, verify-fail, retry/fallback, and safety flags (labs/vitals separation).
2. **Instrumentation pass** — Call `log_agent_event` (or thin wrappers) at RBAC deny paths, verification outcomes, and RGV fallback exits consistent with Phase 3 contracts.
3. **Minimum-questions fields** — Ensure each safety-critical event can answer: what, why, duration, fallback, and cost envelope (or explicit “unknown”) per operator checklist.
4. **Category-boundary flagging** — Log and surface anomalies where cross-category context risks clinical misuse; align with roadmap “flagged for review” expectation.
5. **Operator triage path** — Document how logs/metrics (or a single query pattern) map event types to triage—no requirement to ship a dashboard in this stub’s scope.
6. **RBAC boundary evidence** — Correlate denial telemetry with role+tool identity without leaking PHI in log payloads (`SAFE-rbac-boundary-integrity`).

## Exit Criteria (requirement IDs)
| ID | Done when |
|----|-------------|
| `NFR-observability-coverage` | Denials, verification failures, and fallback events emit structured telemetry with consistent fields across those paths. |
| `NFR-observability-minimum-questions` | Each such event answers: what happened, why, duration, fallback, and cost envelope (or explicit placeholder). |
| `SAFE-rbac-boundary-integrity` | RBAC-related events preserve auditable role/tool context in structured logs without sensitive leakage. |

## Suggested Order
1. Taxonomy + field checklist (minimum questions).
2. Instrument hot paths using `events.py`.
3. Safety flag + triage documentation pass.

## Repo evidence (scaffold)
- `agent/observability/events.py` — `AgentEvent`, `log_agent_event()`.
- `agent/observability/__init__.py` — exports `AgentEvent`, `log_agent_event`.
- `agent/access/rbac.py` — `log_tool_refusal()`; `agent/http/app.py` invokes it on `ToolRefusal`. Integration coverage in `agent/tests/integration/test_http_logging_observability.py` asserts RBAC-denied tool posts log `tool_refusal` with the same structured `event` / `event_type` extras used for `log_agent_event` on chat (parity with chat-turn logging checks in that file).
- `agent/tests/unit/test_events.py` — unit tests for `AgentEvent` and `log_agent_event`.
- `agent/tests/integration/test_http_logging_observability.py` — HTTP-level checks for chat `agent_event` fields and RBAC `tool_refusal` fields.

**Test run (repo state only; not a claim Phase 4 is executed):** `python -m pytest agent/tests -q` → **71 passed, 4 skipped** (local run).
