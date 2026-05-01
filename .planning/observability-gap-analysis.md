# Observability gap analysis (minimum operator questions)

**Date:** 2026-05-01  
**References:** PRD-style expectations in [`.planning/AI-ARCHITECTURE.md`](../.planning/AI-ARCHITECTURE.md), structured logging in `agent/observability/`.

This document maps **required operator questions** to **what exists today** vs **gaps**. No production behavior changes—planning-only.

---

## Minimum questions (rubric)

| Question | Status | Where wired | Gap |
| --- | --- | --- | --- |
| What did the agent do on a specific request, **in order**? | **Partial** | RGV ordering enforced in code (`agent/runtime/rgv_pipeline.py`); chat logs **`chat_turn_complete`** after turn (`agent/services/chat_turn.py`) | No single distributed **trace id** across OpenEMR + agent unless operator correlates `X-Request-ID` / session manually. |
| How long did **each step** take? | **Partial** | **`rgv_duration_ms`** on `CHAT_TURN_COMPLETE` log extras (`agent/tests/integration/test_http_logging_observability.py`) | Per-node retrieve vs generate vs verify breakdown **not** emitted separately in scaffold. |
| Did any **tools** fail, and why? | **Partial** | RBAC denial logs tool refusal events (`test_http_logging_observability.py`); OpenEMR `/api/user` failures → structured auth errors | FHIR tool failures in **fork** not present in scaffold retrieve. |
| How many **tokens** and what **cost**? | **Gap** | `cost_envelope="unknown"` on chat events | Wire OpenAI usage / pricing into logs or exporter (Phase 4–5 roadmap). |

---

## Structured logging inventory (implemented)

| Mechanism | Purpose |
| --- | --- |
| `log_agent_event` / `AgentEvent` | ISO-style **`agent_event`** lines + `event` / `event_type` extras (`agent/observability/events.py`) |
| Taxonomy constants | e.g. `CHAT_TURN_COMPLETE`, `CATEGORY_BOUNDARY_REVIEW`, verify retry (`agent/observability/taxonomy.py`) |
| Counters | `inc_chat_turn`, `inc_verify_failure`, etc. (`agent/observability/metrics_counters.py`) |

---

## Recommended next instrumentation (non-blocking)

1. Emit **phase timings** (`retrieve_ms`, `generate_ms`, `verify_ms`) on `CHAT_TURN_COMPLETE`.
2. When LLM is active, log **token usage** from provider response into `cost_envelope` or sibling fields.
3. Propagate **`X-Request-ID`** consistently (already partially tested) for cross-service grep.

---

## Review cadence

Revisit when Phase 4 (“Observability and Clinical Safety Flagging”) exits or when fork adds real FHIR tools.
