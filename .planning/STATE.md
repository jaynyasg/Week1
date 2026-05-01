# STATE

## Project Reference
- **Core value**: Role-safe clinical copilot integrated with OpenEMR, deployable on Fly.io, with auditable runtime behavior.
- **Canonical policy**: Markdown planning artifacts are authoritative; divergent Word exports are non-authoritative.
- **Current focus**: Complete Phase 3 fork work — real tools, LLM, and verification modules beyond the in-repo scaffold.

## Current Position
- **Current phase**: Phase 3 - Retrieve-Generate-Verify Runtime Flow
- **Current plan**: `.planning/plans/phase-3-retrieve-generate-verify-plan.md`
- **Status**: In progress
- **Progress**: 3/6 phases active (2 complete)
- **Progress bar**: `[###---] 50% active, 33% complete`

## Performance Metrics
- **Phase completion**: 2/6
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
- Wire `agent/runtime/rgv_pipeline.py` into real retrieve + LLM + verify in OpenEMR fork; keep `MAX_VERIFY_RETRIES` aligned with architecture.
- Close `REQ-agent-requirements-coverage` in fork with executable chat + tool + verify path (scaffold alone is not full PRD runtime).
- Define observability minimum-question schema and cost-envelope signals for Phase 4.
- Prepare Phase 5 eval suite expansion (including unauthorized-access tests and Pre-Search Checklist evidence) plus checkpoint cost analysis.

### Known Blockers
- None currently; ingest conflict gate reports 0 unresolved blockers.

## Session Continuity
- **Last completed milestone**: Phase 2 marked complete (RBAC + session + HTTP tests). Phase 3 scaffold: `agent/runtime/rgv_pipeline.py`, `services/chat_turn.py`, `/agent/chat` integration tests + missing-Authorization 401. Gated live E2E: `agent/tests/integration/test_live_openemr_optional.py` — `RUN_LIVE_OPENEMR_E2E=1`, `OPENEMR_BASE_URL`, `OPENEMR_AUTHORIZATION` or `OPENEMR_BEARER_TOKEN` (optional `AGENT_BASE_URL` for remote `/agent/chat`); see root `.env.example`. `REQ-agent-requirements-coverage` stays pending until OpenEMR fork wires real retrieve/LLM/verify.
- **Phase 3 note**: In-repo scaffold vs fork — scaffold proves HTTP/RGV contracts; fork delivers executable coverage against real EMR data paths.
- **Next command target**: `/gsd-execute-phase 3` (fork: real retrieve, LLM generate, programmatic verify).
- **Resume note**: In-repo scaffold satisfies RGV + multi-turn + verify *contracts*; fork integration still required for `REQ-agent-requirements-coverage` and production readiness.
