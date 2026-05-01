# ROADMAP

## Phases
- [x] **Phase 1: Deployment Baseline Hardening** - Lock topology, delivery gates, and private DB posture with smoke validation.
- [ ] **Phase 2: RBAC Enforcement and Test Matrix** - Enforce role-safe tool access at agent runtime.
- [ ] **Phase 3: Retrieve-Generate-Verify Runtime Flow** - Ship bounded retry, multi-turn behavior, and explicit verification contracts.
- [ ] **Phase 4: Observability and Clinical Safety Flagging** - Make denials/failures/quality risks visible and actionable.
- [ ] **Phase 5: Evaluation and Performance Validation** - Prove latency, unauthorized-access resilience, and cost gates.
- [ ] **Phase 6: Documentation Governance Cleanup** - Eliminate markdown-vs-Word drift and lock governance workflow.

## Phase Details

### Phase 1: Deployment Baseline Hardening
**Goal**: Runtime is deployable on Fly.io with private networking guarantees and reproducible smoke validation.
**Depends on**: Nothing
**Requirements**: REQ-deployment-smoke-suite, REQ-delivery-foundation-gates, REQ-ai-integration-plan, REQ-ai-architecture-file, NFR-private-network-topology, NFR-no-public-db-surface, SAFE-demo-only-phi-boundary
**Success Criteria** (what must be TRUE):
  1. OpenEMR and MariaDB run as separate Fly apps communicating over private `.internal` networking only.
  2. No public MariaDB endpoint is reachable from outside Fly private networking.
  3. All seven smoke checks pass after deploy before any checkpoint is marked complete.
  4. MVP delivery gates are met: local OpenEMR runtime with sample data, public deployment readiness, and canonical `AUDIT.md`/`USERS.md`/`ARCHITECTURE.md` availability.
  5. `.planning/AI-ARCHITECTURE.md` exists and defines implementation intent, trust boundaries, and deployment constraints for the AI layer.
  6. Deployment documentation and runtime warnings clearly indicate demo-only data boundaries.
**Plans**: TBD

### Phase 2: RBAC Enforcement and Test Matrix
**Goal**: Access control is enforced at agent execution time for every tool call.
**Depends on**: Phase 1
**Requirements**: REQ-openemr-session-validation, REQ-rbac-agent-layer, REQ-rbac-tool-matrix, REQ-rbac-deny-path
**Success Criteria** (what must be TRUE):
  1. Agent requests without valid OpenEMR session context are rejected before tool execution.
  2. Each role can invoke only the tools allowed by the defined 8-tool RBAC matrix.
  3. ADMIN role access is constrained to demographics and schedule actions as specified.
  4. Denied calls return explicit role+tool refusal responses and produce auditable logs without sensitive leakage.
**Plans**: `.planning/plans/phase-2-rbac-enforcement-plan.md`

### Phase 3: Retrieve-Generate-Verify Runtime Flow
**Goal**: Clinical response generation follows a reliable retrieve/generate/verify loop with bounded retries.
**Depends on**: Phase 2
**Requirements**: REQ-retrieve-generate-verify-loop, REQ-multi-turn-usecase-behavior, REQ-verification-layer-contracts, REQ-agent-requirements-coverage
**Success Criteria** (what must be TRUE):
  1. Every eligible request runs retrieval before generation and verification before final response.
  2. Multi-turn clinician conversations retain valid session/role context and use-case continuity across turns.
  3. Verification enforces domain constraints and includes source attribution plus verification-limit notes in response artifacts.
  4. AI architecture explicitly maps Agentic Chatbot, Verification System, Observability, and Evaluation into executable runtime contracts.
  5. Retry behavior is bounded and terminates deterministically without infinite loops.
  6. Verification failures trigger graceful degradation paths instead of unsafe silent success.
**Plans**: TBD

### Phase 4: Observability and Clinical Safety Flagging
**Goal**: Operational and safety-critical events are observable, queryable, and alertable.
**Depends on**: Phase 3
**Requirements**: NFR-observability-coverage, NFR-observability-minimum-questions, SAFE-rbac-boundary-integrity
**Success Criteria** (what must be TRUE):
  1. RBAC denials, verification failures, and fallback events emit structured telemetry with consistent fields.
  2. Telemetry answers minimum operator questions: what happened, why it happened, how long it took, what fallback triggered, and what cost envelope was incurred.
  3. Safety-relevant category-boundary anomalies (labs/vitals separation risk) are logged and flagged for review.
  4. Operators can identify and triage risk events from logs/metrics without inspecting raw app internals.
**Plans**: TBD

### Phase 5: Evaluation and Performance Validation
**Goal**: Latency and reliability targets are validated with repeatable evaluation evidence.
**Depends on**: Phase 4
**Requirements**: NFR-latency-validation-gate, NFR-eval-suite-unauthorized-access, NFR-cost-analysis-requirement, REQ-presearch-checklist-coverage
**Success Criteria** (what must be TRUE):
  1. Pre-visit summary latency is measured against defined thresholds in a repeatable test harness.
  2. Evaluation suite includes happy-path, failure-mode, regression, and unauthorized-access RBAC test coverage.
  3. Release readiness is blocked when latency/reliability gates or unauthorized-access protections are not met.
  4. Cost analysis artifacts identify primary runtime cost drivers and mitigation options before release checkpoints.
  5. Appendix Pre-Search Checklist items are captured in architecture/eval evidence with explicit pass/fail or rationale status.
  6. Evaluation outputs are stored as artifact evidence for checkpoint review.
**Plans**: TBD

### Phase 6: Documentation Governance Cleanup
**Goal**: Governance prevents requirement/decision drift by treating markdown planning artifacts as authoritative.
**Depends on**: Phase 5
**Requirements**: SAFE-canonical-markdown-governance
**Success Criteria** (what must be TRUE):
  1. Repository governance explicitly states markdown planning docs are canonical over Word exports.
  2. Any divergent Word artifact is either reconciled to markdown or marked non-authoritative.
  3. Planning updates preserve source traceability IDs and cannot silently overwrite ADR/SPEC decisions.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|---|---|---|---|
| 1. Deployment Baseline Hardening | 1/1 | Completed | 2026-04-30 (EMR evidence + AI integration plan finalized) |
| 2. RBAC Enforcement and Test Matrix | 1/1 | In progress | Planned 2026-04-30 |
| 3. Retrieve-Generate-Verify Runtime Flow | 0/1 | Not started | - |
| 4. Observability and Clinical Safety Flagging | 0/1 | Not started | - |
| 5. Evaluation and Performance Validation | 0/1 | Not started | - |
| 6. Documentation Governance Cleanup | 0/1 | Not started | - |
