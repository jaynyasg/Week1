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
