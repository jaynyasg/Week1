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
- Wire `agent/runtime/rgv_pipeline.py` into real retrieve + LLM + verify in OpenEMR fork; keep `MAX_VERIFY_RETRIES` aligned with architecture (ROADMAP Phase 3 still in progress for **full** closure).
- Close `REQ-agent-requirements-coverage` in fork with executable chat + tool + verify path (scaffold alone is not full PRD runtime).
- Phase 4 **remaining** (fork / live stack): operator dashboards, live `Observation.category` validation, correlate deploy events with app logs — in-repo work added **Prometheus counters** on `/agent/metrics` and existing structured events (see `.planning/ROADMAP.md` Progress).
- Phase 5 **remaining**: full eval suite breadth, cost artifacts at release checkpoints, stored eval outputs — in-repo: gated coarse latency test `RUN_LATENCY_GATE=1` (`agent/tests/integration/test_latency_gate_optional.py`), checklist matrix `.planning/PRE-SEARCH-CHECKLIST-EVIDENCE.md`, artifact convention `.planning/eval-artifacts/README.md`.
- Phase 6 **remaining**: Word artifact inventory if external copies exist; traceability spot-checks — in-repo: root `CONTRIBUTING.md` states canonical `.planning/` markdown.

### Known Blockers
- None currently; ingest conflict gate reports 0 unresolved blockers.

### Coordination / parallel work
- **Fly agent deploy bundle (landed in Week1)**: Operator-facing layout is in place — build context via [`Dockerfile.agent`](../Dockerfile.agent), ignore rules in [`.dockerignore.agent`](../.dockerignore.agent), app config in [`fly.agent.toml`](../fly.agent.toml), Python deps in [`deploy/requirements-agent.txt`](../deploy/requirements-agent.txt), and runbook-style notes in [`deploy/README-fly-agent.md`](../deploy/README-fly-agent.md) (read there for env/secrets naming; do not duplicate in STATE).
- **This repo (Week1)**: Phase 3 stays **scaffold** here until fork integration (RGV contracts + tests in-repo; full runtime remains fork-owned — consistent with Session Continuity below). Other Fly manifests still exist for non-agent paths: [`fly.toml`](../fly.toml), [`deploy/fly.toml`](../deploy/fly.toml) (no root `Dockerfile` in-repo; agent image is `Dockerfile.agent` only).
- **Next user actions (agent stack)**: `fly auth login` → `fly apps create <name>` (set `app` in [`fly.agent.toml`](../fly.agent.toml) to that name, or pass `--app <name>` on deploy as the file header documents) → set required Fly secrets per [`deploy/README-fly-agent.md`](../deploy/README-fly-agent.md) → `fly deploy --config fly.agent.toml` → smoke health/chat per that README.
- **Post-deploy verification**:
  - **Public Fly agent base URL (paste yours after deploy; do not guess or invent a hostname):** ________________________________________________
  - Health: `curl -fsS "<same HTTPS origin as the line above>/agent/health"` (substitute the pasted origin only).
  - Optional smoke: `scripts/smoke_agent_service.sh --base-url "<same origin>"` or `powershell -File scripts/smoke_agent_service.ps1 -BaseUrl "<same origin>"`; add `--auth-header` / `-AuthHeader` for chat.
  - Remote chat live test: set `AGENT_BASE_URL` to that same origin when running gated tests in [`agent/tests/integration/test_live_openemr_optional.py`](../agent/tests/integration/test_live_openemr_optional.py) (with `RUN_LIVE_OPENEMR_E2E` and OpenEMR env per root `.env.example`).

## Session Continuity
- **Last completed milestone**: Phases 1–2 complete. Phase 3 **scaffold** in-repo (contracts + tests); **full** Phase 3 closure still fork-owned (SC3 record-backed attribution, `REQ-agent-requirements-coverage`). **2026-05-01**: non-disruptive advance — Phase 3 response-contract tests (`test_scaffold_response_contract.py`), Phase 4 Prometheus counters + wiring, Phase 5 gated latency harness + checklist/eval-artifact docs, Phase 6 `CONTRIBUTING.md`; see ROADMAP Progress table.
- **Agent tests (verified locally)**: `python -m pytest agent/tests deploy/tests -q` — typical **~152 passed**, **~15 skipped** (live OpenEMR, `RUN_LATENCY_GATE`, `RUN_LOAD_TEST`, etc.; run pytest to confirm). Optional: `-m "not eval"` deselects `@pytest.mark.eval` (e.g. latency module when enabled).
- **CI**: `.gitlab-ci.yml` and `.github/workflows/agent-tests.yml` run `ruff check` / `ruff format --check` on `agent/` and `pytest agent/tests deploy/tests`.
- **Observability in repo (Phase 4 partial)**: Structured log extras (`test_http_logging_observability.py`) plus **counter export** on `GET /agent/metrics` (`agent/observability/metrics_counters.py`). Full Phase 4 (operator triage dashboards, live category validation) remains fork/deploy work.
- **Phase 3 scaffold**: `agent/runtime/rgv_pipeline.py`, `services/chat_turn.py`, `/agent/chat` integration tests + missing-Authorization 401. Gated live E2E: `agent/tests/integration/test_live_openemr_optional.py` — `RUN_LIVE_OPENEMR_E2E=1`, `OPENEMR_BASE_URL`, `OPENEMR_AUTHORIZATION` or `OPENEMR_BEARER_TOKEN` (optional `AGENT_BASE_URL`); see root `.env.example`. `REQ-agent-requirements-coverage` stays pending until the fork wires real retrieve/LLM/verify.
- **Phase 3 note**: In-repo scaffold vs fork — scaffold proves HTTP/RGV contracts; fork delivers executable coverage against real EMR data paths.
- **Next command target**: `/gsd-execute-phase 3` (fork: real retrieve, LLM generate, programmatic verify).
- **Resume note**: In-repo scaffold satisfies RGV + multi-turn + verify *contracts*; fork integration still required for `REQ-agent-requirements-coverage` and production readiness.
