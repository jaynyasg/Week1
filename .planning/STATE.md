# STATE

## Project Reference
- **Core value**: Role-safe clinical copilot integrated with OpenEMR, deployable on Fly.io, with auditable runtime behavior.
- **Canonical policy**: Markdown planning artifacts are authoritative; divergent Word exports are non-authoritative.
- **Current focus**: Phase 3 remains **in progress** in Week1: RGV + multi-turn + verify **contracts** and tests are in-repo; **SC3** (record-backed source attribution + real domain verification) and **`REQ-agent-requirements-coverage`** (full PRD runnable path) are **fork / deployed stack** work — see gap tables in `.planning/ROADMAP.md` (Phase 3 Notes) and `.planning/plans/phase-3-retrieve-generate-verify-plan.md`.

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
- Wire `agent/runtime/rgv_pipeline.py` into real retrieve + LLM + verify in OpenEMR fork; keep `MAX_VERIFY_RETRIES` aligned with architecture (ROADMAP Phase 3 still in progress; phases 4–6 not started for execution).
- Close `REQ-agent-requirements-coverage` in fork with executable chat + tool + verify path (scaffold alone is not full PRD runtime).
- Phase 4 execution (per ROADMAP): structured telemetry for denials, failures, fallbacks, minimum operator questions, and cost envelope — beyond current log-extras tests; plan stub: `.planning/plans/phase-4-observability-plan.md`.
- Phase 5–6 (per ROADMAP, not started): eval suite expansion, latency/unauthorized-access/cost gates, Pre-Search Checklist evidence — `.planning/plans/phase-5-evaluation-plan.md`; documentation governance — `.planning/plans/phase-6-documentation-governance-plan.md`.

### Known Blockers
- None currently; ingest conflict gate reports 0 unresolved blockers.

### Coordination / parallel work
- **Fly agent deploy bundle (landed in Week1)**: Operator-facing layout is in place — build context via [`Dockerfile.agent`](../Dockerfile.agent), ignore rules in [`.dockerignore.agent`](../.dockerignore.agent), app config in [`fly.agent.toml`](../fly.agent.toml), Python deps in [`deploy/requirements-agent.txt`](../deploy/requirements-agent.txt), and runbook-style notes in [`deploy/README-fly-agent.md`](../deploy/README-fly-agent.md) (read there for env/secrets naming; do not duplicate in STATE).
- **This repo (Week1)**: Phase 3 stays **scaffold** here until fork integration (RGV contracts + tests in-repo; full runtime remains fork-owned — consistent with Session Continuity below). Other Fly manifests still exist for non-agent paths: [`fly.toml`](../fly.toml), [`deploy/fly.toml`](../deploy/fly.toml) (no root `Dockerfile` in-repo; agent image is `Dockerfile.agent` only).
- **Next user actions (agent stack)**: `fly auth login` → `fly apps create <name>` (set `app` in [`fly.agent.toml`](../fly.agent.toml) to that name, or pass `--app <name>` on deploy as the file header documents) → set required Fly secrets per [`deploy/README-fly-agent.md`](../deploy/README-fly-agent.md) → `fly deploy --config fly.agent.toml` → smoke health/chat per that README.

## Session Continuity
- **Last completed milestone**: Per ROADMAP, Phases 1–2 are completed; Phase 3 is in progress (RGV scaffold + tests in repo, not the full fork runtime). **2026-04-30 gap review**: Phase 3 **not** closed in this repo — SC3 + `REQ-agent-requirements-coverage` remain fork-owned (see ROADMAP Phase 3 Notes gap table and `phase-3-retrieve-generate-verify-plan.md`). Phases 4–6 remain not started for execution; plan stubs are linked from ROADMAP: `phase-4-observability-plan.md`, `phase-5-evaluation-plan.md`, `phase-6-documentation-governance-plan.md` under `.planning/plans/`.
- **Agent tests (verified locally)**: `python -m pytest agent/tests -q` → **75 passed, 4 skipped** (same command as README and CI). Skips align with optional/gated tests (e.g. live OpenEMR E2E).
- **CI**: `.gitlab-ci.yml` (GitLab) and `.github/workflows/agent-tests.yml` (GitHub) run `python -m pytest agent/tests`.
- **Observability in repo (tests, not Phase 4 completion)**: `agent/tests/integration/test_http_logging_observability.py` asserts structured log extras on `/agent/chat` (`chat_turn_complete`) and on RBAC tool denial (`tool_refusal` / 403 on `/agent/tools/labs`), using `agent.observability.events` keys — contract-level coverage only; ROADMAP Phase 4 success criteria are still outstanding.
- **Phase 3 scaffold**: `agent/runtime/rgv_pipeline.py`, `services/chat_turn.py`, `/agent/chat` integration tests + missing-Authorization 401. Gated live E2E: `agent/tests/integration/test_live_openemr_optional.py` — `RUN_LIVE_OPENEMR_E2E=1`, `OPENEMR_BASE_URL`, `OPENEMR_AUTHORIZATION` or `OPENEMR_BEARER_TOKEN` (optional `AGENT_BASE_URL`); see root `.env.example`. `REQ-agent-requirements-coverage` stays pending until the fork wires real retrieve/LLM/verify.
- **Phase 3 note**: In-repo scaffold vs fork — scaffold proves HTTP/RGV contracts; fork delivers executable coverage against real EMR data paths.
- **Next command target**: `/gsd-execute-phase 3` (fork: real retrieve, LLM generate, programmatic verify).
- **Resume note**: In-repo scaffold satisfies RGV + multi-turn + verify *contracts*; fork integration still required for `REQ-agent-requirements-coverage` and production readiness.
