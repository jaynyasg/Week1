# Phase 5 Execution Plan — Evaluation and Performance Validation

## Objective
Prove **latency**, **unauthorized-access resilience**, **cost envelopes**, **Pre-Search Checklist coverage**, and **evaluation artifact storage** with repeatable harnesses and checkpoint-ready evidence—after observability (Phase 4) makes failures measurable.

## Non-Goals
- Replacing Phase 4 telemetry contracts or redefining RBAC matrix (Phase 2).
- Production Langfuse/dashboard builds unless they directly serve evaluation artifact retention.

## Current Baseline (Week1 repo)
- Roadmap success criteria define gates for pre-visit summary latency, eval-suite breadth (including unauthorized-access), cost artifacts, checklist traceability, and stored evaluation outputs; this stub sequences work against those IDs without prescribing implementation files yet.

## Work Items
1. **Latency harness** — Repeatable measurement of pre-visit summary latency against defined thresholds; gate release when thresholds fail (`NFR-latency-validation-gate`).
2. **Eval suite breadth** — Happy-path, failure-mode, regression, and **unauthorized-access / RBAC** cases in one runnable suite; block release when protections or reliability gates fail (`NFR-eval-suite-unauthorized-access`).
3. **Cost analysis** — Artifacts naming primary runtime cost drivers and mitigation options at release checkpoints (`NFR-cost-analysis-requirement`).
4. **Pre-Search Checklist** — Map appendix checklist items to architecture/eval evidence with explicit pass/fail or rationale (`REQ-presearch-checklist-coverage`).
5. **Artifact storage** — Persist evaluation outputs (logs, summaries, cost/latency reports) as reviewable evidence for checkpoint sign-off (aligns with roadmap success criterion 6).

## Exit Criteria (requirement IDs)
| ID | Done when |
|----|-------------|
| `NFR-latency-validation-gate` | Pre-visit summary latency is measured against defined thresholds in a repeatable test harness; release blocked when not met. |
| `NFR-eval-suite-unauthorized-access` | Suite includes happy-path, failure-mode, regression, and unauthorized-access RBAC coverage; gates enforce failures. |
| `NFR-cost-analysis-requirement` | Cost analysis artifacts identify primary drivers and mitigations before release checkpoints. |
| `REQ-presearch-checklist-coverage` | Appendix Pre-Search Checklist items appear in architecture/eval evidence with pass/fail or rationale. |

## Suggested Order
1. Latency harness + gate wiring.
2. Expand eval suite (including unauthorized-access).
3. Cost artifact template + first run.
4. Checklist-to-evidence matrix; store all outputs as checkpoint artifacts.

## Repo evidence (scaffold)
- **RBAC / denial (HTTP):** `agent/tests/integration/test_tool_route_rbac.py` — `/agent/tools/{tool_name}` dependency overrides; asserts `403` on disallowed tools.
- **RBAC / denial (logging):** `agent/tests/integration/test_http_logging_observability.py` — e.g. `test_post_agent_tools_rbac_403_logs_tool_refusal_with_event_field` asserts `403` and log extras for tool refusal.
- **RBAC matrix (unit):** `agent/tests/unit/test_rbac_matrix.py` — parameterized matrix vs `USERS.md`; partial-denial / `assert_tools_allowed` coverage.
- **Observability HTTP tests:** same file `agent/tests/integration/test_http_logging_observability.py` for request/response logging behavior.
- **Live OpenEMR (gated, optional):** `agent/tests/integration/test_live_openemr_optional.py` — enabled when `RUN_LIVE_OPENEMR_E2E` or `RUN_LIVE_OPENEMR_TESTS` is set (and related auth env); not required for default CI runs.
- **CI — GitHub Actions:** `.github/workflows/agent-tests.yml` runs `python -m ruff check agent` and `python -m pytest agent/tests deploy/tests -q` (see workflow jobs).
- **CI — GitLab:** `.gitlab-ci.yml` runs ruff + pytest on `agent/tests` and `deploy/tests` in the test job (live OpenEMR job commented with pointer to the optional test file).
- **Post-deploy smoke (minimal release gate):** In the evaluation story, treat post-deploy smoke—`/agent/health` plus optional `/agent/chat` exercised with real auth—as a minimal release gate after ship; scripts `scripts/smoke_agent_service.ps1` and `scripts/smoke_agent_service.sh`, with operator notes in `deploy/README-fly-agent.md`.

### Pytest snapshot (repo state, not Phase 5 completion)
- Command: `python -m pytest agent/tests deploy/tests -q`; lint: `python -m ruff check agent`
- Typical local run (approximate): ~**152 passed**, ~**15 skipped**—counts vary; run pytest to confirm. Skips reflect optional live OpenEMR, `RUN_LATENCY_GATE`, and other gated tests, not a claim that Phase 5 exit criteria are met. Optional scheduled workflow: `.github/workflows/latency-gate-scheduled.yml`. GitLab: **`latency-gate`** job (`schedule` or **manual**).
