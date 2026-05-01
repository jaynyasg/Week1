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
5. **Operator triage path** — Document how logs/metrics (or a single query pattern) map event types to triage—no requirement to ship a dashboard in this stub’s scope. **Done (repo):** `deploy/README-fly-agent.md` section *Operator triage (structured logs)*.
6. **RBAC boundary evidence** — Correlate denial telemetry with role+tool identity without leaking PHI in log payloads (`SAFE-rbac-boundary-integrity`).
7. **OpenEMR base URL misconfiguration** — Today a bad `OPENEMR_BASE_URL` yields **HTTP 500** from FastAPI; Phase 4 should add **structured operator-facing telemetry** with a distinct `event_type`, duration, and request id—**without** logging secrets. Current contract: `agent/tests/integration/test_openemr_base_url_misconfiguration.py`.

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
- `agent/observability/metrics_counters.py` — thread-safe counters; `GET /agent/metrics` appends Prometheus `# HELP` / `# TYPE counter` lines (chat turns, RBAC refusals, verify failures, RGV degraded, category-boundary flags, OpenEMR auth failures).
- `agent/observability/events.py` — `AgentEvent`, `log_agent_event()`.
- `agent/observability/__init__.py` — exports `AgentEvent`, `log_agent_event`.
- `agent/access/rbac.py` — `log_tool_refusal()`; `agent/http/app.py` invokes it on `ToolRefusal`. Integration coverage in `agent/tests/integration/test_http_logging_observability.py` asserts RBAC-denied tool posts log `tool_refusal` with the same structured `event` / `event_type` extras used for `log_agent_event` on chat (parity with chat-turn logging checks in that file).
- `agent/tests/unit/test_events.py` — unit tests for `AgentEvent` and `log_agent_event`.
- `agent/tests/integration/test_http_logging_observability.py` — HTTP-level checks for chat `agent_event` fields and RBAC `tool_refusal` fields.
- `.github/workflows/fly-agent-manual.yml` — GitHub **fly-agent-manual** workflow provides an **audit trail** in Actions logs (who/when a deploy ran); Phase 4 should later correlate deploy events with app logs (fork).

**Test run (repo state):** `python -m pytest agent/tests deploy/tests -q`; lint: `python -m ruff check agent`. Typical local run ~**152 passed**, ~**15 skipped** (approximate—counts vary). CI runs ruff + pytest on both test dirs (`.github/workflows/agent-tests.yml`, `.gitlab-ci.yml`) with **JUnit** artifacts; optional non-blocking **pip/npm audit** jobs. Instrumentation for verify/retry/degrade, misconfig (incl. client request id), category scaffold, RBAC minimum-question fields, **Prometheus counters** on `/agent/metrics` (incl. `openemr_misconfiguration_total`, `client_missing_credentials_total`), **dependency log integration tests**, and **minimum-question log contract tests** is in-tree; hosted dashboards / trace backends remain fork-optional.
