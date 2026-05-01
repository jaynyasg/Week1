# PROJECT

## Core Value
Clinical Co-Pilot provides role-safe, session-validated clinical assistance on top of OpenEMR, with deployable infrastructure and auditable behavior.

## Canonical Source Policy
- Markdown artifacts in this repository are canonical.
- Divergent Word exports are non-authoritative and must not override markdown decisions, requirements, or runbooks.

## Locked Direction from Ingest
- `DEC-deploy-fly-io`: Deploy on Fly.io.
- `DEC-two-app-private-topology`: Run OpenEMR and MariaDB as separate Fly apps over private `.internal` networking.
- `DEC-no-public-db-service`: Keep MariaDB private; no public service exposure.

## In-Scope V1 Outcomes
- Harden deployment baseline and prove smoke-test readiness.
- Require an AI integration plan and a dedicated AI architecture artifact for implementation intent.
- Enforce RBAC at the agent layer with explicit deny behavior.
- Deliver retrieve/generate/verify orchestration with bounded retries, multi-turn continuity, and explicit verification contracts.
- Ensure AI architecture covers all PRD agent requirements: Agentic Chatbot, Verification System, Observability, and Evaluation.
- Add observability and safety flagging for RBAC and clinical-response risks, including minimum operator questions for timing/failure/cost triage.
- Validate latency/performance targets, unauthorized-access resilience, and delivery gates before release promotion.
- Produce lightweight cost analysis evidence for deployment/runtime choices before release gating.
- Integrate Appendix Pre-Search Checklist constraints into planning, architecture decisions, and evaluation gates.
- Eliminate planning drift via documentation governance cleanup.

## Constraints and Assumptions
- Demo-only data unless HIPAA BAA and controls are explicitly added (`ASM-demo-only-data`).
- Observation category quality must sustain labs/vitals boundaries (`ASM-observation-category-integrity`).

## Current Focus
Bootstrap executable planning artifacts from synthesized ingest for immediate phase planning and execution.

## Agent tests (snapshot)
- Command: `python -m pytest agent/tests -q`
- Last verified (local): 71 passed, 4 skipped
- CI: `.github/workflows/agent-tests.yml`, `.gitlab-ci.yml`

## Agent deploy (Fly)
- Manual deploy: `.github/workflows/fly-agent-manual.yml` (`workflow_dispatch`; repo secret `FLY_API_TOKEN`), config `fly.agent.toml`, runbook `deploy/README-fly-agent.md`.

## Fork / workable deployment checklist

Ordered fork work to reach a **workable deployment** (thin MVP vs production-shaped). Assumptions unless noted: **one dedicated engineer**, scope limited to this repo’s agent + deployment surface (no greenfield EMR rewrite), existing CI/agent tests as baseline.

1. **FHIR retrieve + RBAC** — Wire authenticated FHIR reads (or equivalent clinical data path) with session-scoped RBAC, explicit deny paths, and tests that prove role boundaries; align with deployment topology (private services, no accidental public DB).
2. **LLM generate** — Stable model routing, prompts, timeouts/retries, and secrets/config per environment; smoke path from “authorized request → model call → structured response.”
3. **Real verify / grounding** — Verification contracts against retrieved facts (not stub-only): grounding checks, refusal/uncertainty behavior, and bounded retries consistent with orchestration goals.
4. **`/agent/chat` production wiring** — HTTP surface, auth, rate limits or backpressure as needed, health/readiness, and Fly (or chosen host) config so the agent API is reachable only as intended (no dev-only shortcuts).
5. **`REQ-agent-requirements-coverage`** — Trace PRD/agent requirements to implemented behavior and tests; close gaps before calling the fork “feature-complete” for agent scope.
6. **Phase 4 telemetry (misconfig + refusals)** — Metrics/logs/traces for RBAC denials, misconfiguration signals, model errors, and clinical-safety refusals so operators can triage timing, failure, and cost.
7. **Phase 5 eval gates** — Automated or scripted eval runs (latency, unauthorized access, verification quality) tied to release promotion; cost/latency evidence per planning gates.

**Rough duration guidance** (ranges; same engineer/scope assumptions as above):

| Track | Thin MVP (fork “runs end-to-end in prod-like env”) | Production-shaped (RBAC hardening, telemetry, eval gates, requirement traceability) |
|-------|------------------------------------------------------|-------------------------------------------------------------------------------------|
| Items 1–3 (retrieve, generate, verify) | ~2–4 weeks | ~5–10 weeks |
| Item 4 (`/agent/chat` + hosting) | ~1–2 weeks (if infra patterns exist) | ~2–4 weeks (hardening, SLOs, runbooks) |
| Items 5–7 (requirements coverage, Phase 4 telemetry, Phase 5 eval) | ~2–4 weeks partial (minimal dashboards + one eval pass) | ~4–8 weeks (full coverage, alerting, repeatable eval pipeline) |

**Combined fork-to-workable:** **~5–10 weeks** thin MVP (happy path, minimal observability/eval) vs **~12–22 weeks** production-shaped (overlapping work can shorten wall time with parallelization or lengthen if EMR/FHIR integration is novel to the team). Add buffer if HIPAA/BAA or new clinical data contracts apply beyond demo assumptions.
