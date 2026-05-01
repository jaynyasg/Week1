# STATE

## Project Reference
- **Core value**: Role-safe clinical copilot integrated with OpenEMR, deployable on Fly.io, with auditable runtime behavior.
- **Canonical policy**: Markdown planning artifacts are authoritative; divergent Word exports are non-authoritative.
- **Current focus**: Execute Phase 2 RBAC enforcement and test-matrix planning.

## Current Position
- **Current phase**: Phase 2 - RBAC Enforcement and Test Matrix
- **Current plan**: `.planning/plans/phase-2-rbac-enforcement-plan.md`
- **Status**: In progress
- **Progress**: 2/6 phases active (1 complete)
- **Progress bar**: `[##----] 33% active, 17% complete`

## Performance Metrics
- **Phase completion**: 1/6
- **Requirements mapped**: 23/23
- **Coverage health**: 100% mapped, no orphaned requirements
- **Critical risk watch**: `RISK-word-markdown-source-drift`, `RISK-observation-category-drift`, `RISK-summary-latency-unverified`, `RISK-unauthorized-access-regression`, `RISK-cost-blind-release`

## Accumulated Context

### Key Decisions
- `DEC-deploy-fly-io`
- `DEC-two-app-private-topology`
- `DEC-no-public-db-service`

### Active Constraints
- Demo-only data boundary until HIPAA BAA controls exist (`ASM-demo-only-data`).
- Observation category quality must preserve RBAC boundaries (`ASM-observation-category-integrity`).
- Deployed OpenEMR base URL for agent session checks: `https://clinical-copilot-v2.fly.dev` (see root `.env.example` and `deploy/.env.example` for `OPENEMR_BASE_URL` / `DEPLOYED_URL`).

### Current TODOs
- Execute `.planning/plans/phase-2-rbac-enforcement-plan.md` task groups 1-4.
- Define Phase 3 multi-turn + verification-layer contract tests tied to clinical use cases.
- Define observability minimum-question schema and cost-envelope signals for Phase 4.
- Prepare Phase 5 eval suite expansion (including unauthorized-access tests and Pre-Search Checklist evidence) plus checkpoint cost analysis.

### Known Blockers
- None currently; ingest conflict gate reports 0 unresolved blockers.

## Session Continuity
- **Last completed milestone**: Phase 2 core implementation — RBAC module, OpenEMR session helper, minimal FastAPI `/agent/tools/{tool}` gate + HTTP integration tests (`pytest agent/tests`, 44 passed).
- **Next command target**: `/gsd-execute-phase 2` (continue wiring RBAC into FastAPI retrieve/dispatch + integration tests).
- **Resume note**: Import `assert_tool_allowed` / `validate_session_and_resolve_role` from the agent package into the live graph; add integration tests against the real app when the OpenEMR fork + agent service land in-repo.
