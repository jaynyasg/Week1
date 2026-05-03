# AI-ARCHITECTURE

## Purpose
This file is the AI integration plan and implementation-intent architecture for the Clinical Co-Pilot. It defines how the agent addresses the case study and how we enforce trust, safety, operability, and evaluation gates.

## Scope and Inputs
- Primary inputs: `ARCHITECTURE.md`, `USERS.md`, `AUDIT.md`, `PRD-AgentForge-Clinical-CoPilot-Requirements.md`.
- Canonicality: repository markdown is authoritative over non-markdown exports.
- Deployment posture: demo-data boundary remains active until production compliance controls are explicitly added.

## AI System Overview
- **Agent placement**: FastAPI agent service integrated with OpenEMR via authenticated API boundary.
- **Core runtime**: retrieve -> generate -> verify flow with bounded retry and explicit failure handling.
- **Session model**: per-patient and per-role scoped context with reset behavior on chart/patient boundary changes.
- **Trust boundaries**: OpenEMR auth boundary, tool authorization boundary, verification boundary, and output boundary.

## Implemented scaffold (2026-05) — tools and auth

- **Model-invokable tools (five):** `get_patient_demographics`, `list_active_medications`, `list_recent_laboratory_results`, `list_recent_vital_signs`, `list_allergies` — OpenAI function schemas and execution in [`agent/tools/dispatch.py`](../agent/tools/dispatch.py); data from **CSV/Synthea fixtures** or **OpenEMR FHIR R4** when client credentials are set (see [`deploy/README-fly-agent.md`](../deploy/README-fly-agent.md) FHIR section).
- **Auth to agent:** (1) **Cookie / session probe** — [`deploy/copilot_session_probe.php`](../deploy/copilot_session_probe.php); (2) **Bearer** — Standard API user route; (3) **Demo bypass** — `AGENT_DEMO_BYPASS` + `X-Agent-Demo-Role` only for non-PHI demos. Details in [`agent/access/openemr_auth.py`](../agent/access/openemr_auth.py), [`agent/http/deps.py`](../agent/http/deps.py).
- **Demo workflows:** [`deploy/CLINICIAN-WORKFLOWS.md`](../deploy/CLINICIAN-WORKFLOWS.md).
- **Behavioral evals:** [`EVAL.md`](../EVAL.md) — 53 core + 21 edge-case tests under `agent/tests/eval/`.

## PRD Agent Requirements Coverage

**Phase 3 scope (gap review 2026-04-30, aligned with `.planning/ROADMAP.md`)**: This repository documents **PRD-aligned design intent** and ships **scaffold + HTTP/contracts + automated tests** for retrieve–generate–verify and chat (e.g. ordering, multi-turn session headers, structured verification fields, bounded retry, degradation paths). It does **not** close the full **executable** PRD agent path (production LLM, FHIR-backed retrieve, record-backed source attribution in response artifacts, domain-grounded verify module). That **runtime** work is **OpenEMR fork / deployed-stack** ownership—treat in-repo behavior as **scaffold and contract proof**, not full PRD runtime parity.

### 1) Agentic Chatbot
- Multi-turn conversational behavior is required and must be justified by concrete clinical use cases.
- Turn state must preserve role/session context and user intent continuity.
- Tool chaining is allowed only where use-case traceability exists in `USERS.md`.

### 2) Verification System
- Every factual claim must map to record-backed source attribution.
- Domain constraint checks run pre-response; non-compliant outputs are blocked or degraded safely.
- Verification limits are surfaced as structured notes for operator review and eval analysis.

### 3) Observability
- Minimum operator questions must always be answerable:
  - What happened?
  - Why did it pass/fail?
  - How long did each step take?
  - What fallback/degradation path triggered?
  - What cost envelope was incurred?
- Events include RBAC denials, tool failures, verification failures, and fallback actions.

### 4) Evaluation
- Eval scope includes happy path, failure modes, regressions, and unauthorized-access attempts.
- Release gating depends on measured latency/reliability thresholds plus safety policy adherence.
- Eval artifacts are retained as evidence for milestone/checkpoint defensibility.
- **In-repo pack:** [`EVAL.md`](../EVAL.md) inventories **53** core + **21** edge-case behavioral tests (`agent/tests/eval/`).

## Deployment Intent for AI Layer
- AI behavior in deployed environments must match planned runtime contracts.
- Deployment gates include smoke tests, auth/RBAC enforcement checks, and observability validation.
- Cost analysis artifacts must be maintained for release checkpoints.
- Non-goal for Phase 1 closeout: no OpenEMR/MariaDB redeploy is required when existing deployment evidence is valid.

## Phase 1 Delivery-Gate Alignment
- `REQ-delivery-foundation-gates` (AI portion) is satisfied by this file plus existing canonical artifacts:
  - `AUDIT.md` (risk and compliance baseline)
  - `USERS.md` (user/workflow and role boundaries)
  - `ARCHITECTURE.md` (system architecture intent)
- `REQ-ai-integration-plan` is satisfied by this file and `.planning/plans/phase-1-ai-integration-plan.md`.
- `REQ-ai-architecture-file` is satisfied by maintaining this file as the canonical AI implementation-intent artifact.

## Requirement Traceability (Phase 1 AI)

| Requirement ID | Implementation Section(s) | Status |
|---|---|---|
| `REQ-delivery-foundation-gates` (AI portion) | Purpose, Scope and Inputs, Deployment Intent for AI Layer, Phase 1 Delivery-Gate Alignment | Satisfied |
| `REQ-ai-integration-plan` | Purpose, AI System Overview, PRD Agent Requirements Coverage, Appendix Pre-Search Checklist Integration | Satisfied (planning artifact); executable AI/runtime parity follows Phase 3 scaffold → **fork** per roadmap |
| `REQ-ai-architecture-file` | Entire document (`.planning/AI-ARCHITECTURE.md`) | Satisfied |
| `REQ-agent-requirements-coverage` | PRD Agent Requirements Coverage (sections 1–4): PRD **design and contract** mapping; in-repo **scaffold + tests** only for RGV/chat | **Partial** — **not met (runtime)** for full PRD tool+LLM+verify path and record-backed attribution; remainder **OpenEMR fork** (Phase 3 gap table, 2026-04-30) |
| `REQ-presearch-checklist-coverage` | Appendix Pre-Search Checklist Integration (items 1-16) | Satisfied (explicit checklist gates in this doc); item-level **execution** (eval harness, telemetry, production verification) is phased in roadmap Phases 4–5 |

## Evidence Linkage (Deployment, Safety, and Agent Evidence)

Deployment and safety rows below reflect **completed** baseline linkage. The agent row reflects **Partial** in-repo **scaffold + doc** evidence and **fork** ownership for full PRD runtime (Phase 3 gap review, 2026-04-30).

| Requirement ID | Evidence Source(s) | Status |
|---|---|---|
| `REQ-deployment-smoke-suite` | `deploy/docs/deployment.md`, `deploy/INSTALL.md`, `AUDIT.md` | Linked (already completed) |
| `NFR-private-network-topology` | `deploy/docs/deployment.md`, `ARCHITECTURE.md` | Linked (already completed) |
| `NFR-no-public-db-surface` | `deploy/docs/deployment.md`, `ARCHITECTURE.md` | Linked (already completed) |
| `SAFE-demo-only-phi-boundary` | `AUDIT.md`, `deploy/docs/deployment.md`, Scope and Inputs section in this file | Linked (already completed) |
| `REQ-agent-requirements-coverage` | This file (PRD Agent Requirements Coverage + Phase 3 scope note); Phase 3 plan `.planning/plans/phase-3-retrieve-generate-verify-plan.md`; in-repo **scaffold/tests** (e.g. `agent/runtime/rgv_pipeline.py`, `agent/tests/` per roadmap SC1–SC3 / REQ-* rows) | **Partial (scaffold + doc)** — **fork** for full runtime PRD path and record-backed verification in live responses |

## Appendix Pre-Search Checklist Integration
Each checklist area is treated as a design gate with explicit status tracking:

1. **Domain Selection**: in-scope use cases, workflow grounding, and “why conversational agent” per use case in **`USERS.md` Part 1** (single source of truth); RBAC/tool matrix in **`USERS.md` Part 2**.
2. **Scale and Performance**: latency targets, concurrency expectations, and cost limits tracked in roadmap phases 1 and 5.
3. **Reliability Requirements**: wrong-answer impact and non-negotiable verification constraints documented in `AUDIT.md` and this file.
4. **Team and Skill Constraints**: framework and operational choices constrained to delivery-safe complexity.
5. **Agent Framework Selection**: runtime state, tool orchestration, and retry mechanics documented in architecture artifacts.
6. **LLM Selection**: model behavior, context, and cost implications captured in architecture and cost-analysis outputs.
7. **Tool Design**: tool scope, error handling, and API dependencies traced to use cases and RBAC policy.
8. **Observability Strategy**: instrumentation and operator-question coverage are mandatory.
9. **Eval Approach**: measurable pass/fail gates and edge-case coverage are mandatory.
10. **Verification Design**: claim classes, rule enforcement, and escalation logic are explicit.
11. **Failure Mode Analysis**: failure/degradation behavior is designed and tested.
12. **Security Considerations**: prompt-injection, data-leakage, and secret-handling controls are planned and verified.
13. **Testing Strategy**: unit, integration, adversarial, and regression tests are planned by phase.
14. **Open Source Planning**: deliverable and documentation obligations remain explicit.
15. **Deployment and Operations**: hosting, monitoring, and rollback paths are part of release readiness.
16. **Iteration Planning**: eval-driven improvements and prioritization are required for ongoing work.

## Exit Criteria
This architecture file is considered complete for V1 planning only when:
- PRD agent requirements are mapped to **design, contracts, and in-repo scaffold/tests** where this repository delivers them, with **fork/deployed-stack** called out for **full runtime** PRD parity (not overstated as fully executable here).
- Pre-Search checklist coverage is explicit and phase-aligned.
- Deployment, observability, verification, and evaluation gates are represented in roadmap requirements.
- Phase 1 delivery-gate AI requirements have explicit traceability and evidence linkage without requiring EMR redeploy.
