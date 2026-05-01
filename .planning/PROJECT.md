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
