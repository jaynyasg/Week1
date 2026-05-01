# REQUIREMENTS

## Scope
V1 requirements are derived from `.planning/ingest/synthesis.json` with ADR/SPEC precedence preserved.

## Canonical Source Policy
- Markdown artifacts in-repo are canonical.
- Word exports are reference-only and non-authoritative when divergent.

## Functional Requirements (V1)
- `REQ-deployment-smoke-suite`: All seven deployment smoke tests pass after each deploy before checkpoint submission.
- `REQ-delivery-foundation-gates`: MVP delivery gates require local OpenEMR runtime with sample data, public deployment readiness, and canonical `AUDIT.md`/`USERS.md`/`ARCHITECTURE.md` artifacts.
- `REQ-ai-integration-plan`: Planning baseline must include an explicit AI integration plan that maps architecture choices to case-study constraints and delivery gates.
- `REQ-ai-architecture-file`: Repository must include `.planning/AI-ARCHITECTURE.md` as the implementation-intent file for the AI agent.
- `REQ-openemr-session-validation`: Agent auth validates OpenEMR session tokens through `/api/user`.
- `REQ-rbac-agent-layer`: RBAC is enforced at the agent layer (not UI-only).
- `REQ-rbac-tool-matrix`: Tool permissions follow the 8-tool matrix; ADMIN scope is limited to demographics and schedule.
- `REQ-rbac-deny-path`: Denied tool calls return explicit role+tool refusals and are logged without side-channel leakage.
- `REQ-retrieve-generate-verify-loop`: Runtime executes retrieve -> generate -> verify with bounded retry and graceful degradation.
- `REQ-multi-turn-usecase-behavior`: Multi-turn agent behavior must preserve role/session context and use-case intent across successive clinician prompts.
- `REQ-verification-layer-contracts`: Verification layer must enforce pre-response domain checks, attach source attribution, and expose verification-limit notes for review.
- `REQ-agent-requirements-coverage`: AI architecture must explicitly cover Agentic Chatbot, Verification System, Observability, and Evaluation requirements from the PRD.
- `REQ-presearch-checklist-coverage`: AI architecture must address Appendix Pre-Search Checklist items as explicit design constraints, assumptions, and validation hooks.

## Non-Functional Requirements (V1)
- `NFR-private-network-topology`: OpenEMR/MariaDB run as separate Fly apps on private `.internal` network paths only.
- `NFR-no-public-db-surface`: MariaDB exposes no public service endpoint.
- `NFR-observability-coverage`: RBAC denials, verification failures, and fallback paths emit structured events suitable for alerting.
- `NFR-observability-minimum-questions`: Telemetry must answer minimum operator questions for each run: what happened, why it failed/passed, how long it took, what fallback triggered, and what the run cost envelope was.
- `NFR-eval-suite-unauthorized-access`: Evaluation suite must cover happy path, failure modes, regressions, and unauthorized-access attempts against RBAC/tool boundaries.
- `NFR-latency-validation-gate`: Pre-visit summary latency target must be measured and pass defined acceptance thresholds before release.
- `NFR-cost-analysis-requirement`: Release checkpoints require cost analysis artifacts covering per-request/runtime cost drivers and mitigation options.

## Safety and Compliance Constraints (V1)
- `SAFE-demo-only-phi-boundary`: No real PHI in deployed environments until HIPAA BAA and controls are in place.
- `SAFE-rbac-boundary-integrity`: Labs/vitals access controls must be validated against `Observation.category` tagging behavior.
- `SAFE-canonical-markdown-governance`: Planning and implementation governance must resolve markdown-vs-Word drift in favor of markdown authority.

## Source Traceability

| ID | Type | Source IDs | Source Document(s) |
|---|---|---|---|
| REQ-deployment-smoke-suite | Functional | REQ-deployment-smoke-suite | `deploy/docs/deployment.md` |
| REQ-delivery-foundation-gates | Functional | REQ-mvp-foundation-gates | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| REQ-ai-integration-plan | Functional | REQ-ai-integration-plan | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| REQ-ai-architecture-file | Functional | REQ-ai-integration-plan | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| REQ-openemr-session-validation | Functional | REQ-openemr-session-validation | `ARCHITECTURE.md` |
| REQ-rbac-agent-layer | Functional | REQ-rbac-agent-layer | `USERS.md` |
| REQ-rbac-tool-matrix | Functional | REQ-rbac-tool-matrix | `USERS.md` |
| REQ-rbac-deny-path | Functional | REQ-rbac-deny-path | `USERS.md` |
| REQ-retrieve-generate-verify-loop | Functional | REQ-retrieve-generate-verify-loop | `ARCHITECTURE.md` |
| REQ-multi-turn-usecase-behavior | Functional | REQ-rbac-boundaries | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| REQ-verification-layer-contracts | Functional | REQ-verifiable-outputs | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| REQ-agent-requirements-coverage | Functional | REQ-agent-requirements | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| REQ-presearch-checklist-coverage | Functional | REQ-appendix-presearch-checklist | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| NFR-private-network-topology | Non-functional | DEC-two-app-private-topology | `deploy/docs/deployment.md` |
| NFR-no-public-db-surface | Non-functional | DEC-no-public-db-service | `deploy/docs/deployment.md` |
| NFR-observability-coverage | Non-functional | RISK-observation-category-drift, RISK-summary-latency-unverified | `AUDIT.md` |
| NFR-observability-minimum-questions | Non-functional | REQ-observability-and-eval | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| NFR-eval-suite-unauthorized-access | Non-functional | REQ-observability-and-eval | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| NFR-latency-validation-gate | Non-functional | RISK-summary-latency-unverified | `AUDIT.md` |
| NFR-cost-analysis-requirement | Non-functional | REQ-observability-and-eval | `PRD-AgentForge-Clinical-CoPilot-Requirements.md` |
| SAFE-demo-only-phi-boundary | Safety/Compliance | ASM-demo-only-data | `deploy/docs/deployment.md` |
| SAFE-rbac-boundary-integrity | Safety/Compliance | ASM-observation-category-integrity, RISK-observation-category-drift | `AUDIT.md` |
| SAFE-canonical-markdown-governance | Safety/Compliance | RISK-word-markdown-source-drift | `AUDIT.md` |

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| REQ-deployment-smoke-suite | Phase 1 | Completed (evidence-based) |
| REQ-delivery-foundation-gates | Phase 1 | Completed (evidence-based) |
| REQ-ai-integration-plan | Phase 1 | Completed (evidence-based) |
| REQ-ai-architecture-file | Phase 1 | Completed (evidence-based) |
| REQ-openemr-session-validation | Phase 2 | Completed (evidence-based) |
| REQ-rbac-agent-layer | Phase 2 | Completed (evidence-based) |
| REQ-rbac-tool-matrix | Phase 2 | Completed (evidence-based) |
| REQ-rbac-deny-path | Phase 2 | Completed (evidence-based) |
| REQ-retrieve-generate-verify-loop | Phase 3 | Completed (scaffold + unit tests) |
| REQ-multi-turn-usecase-behavior | Phase 3 | Completed (scaffold + unit tests) |
| REQ-verification-layer-contracts | Phase 3 | Completed (injectable verify + notes; scaffold) |
| REQ-agent-requirements-coverage | Phase 3 | Pending |
| REQ-presearch-checklist-coverage | Phase 5 | Pending |
| NFR-private-network-topology | Phase 1 | Completed (evidence-based) |
| NFR-no-public-db-surface | Phase 1 | Completed (evidence-based) |
| NFR-observability-coverage | Phase 4 | Pending |
| NFR-observability-minimum-questions | Phase 4 | Pending |
| NFR-eval-suite-unauthorized-access | Phase 5 | Pending |
| NFR-latency-validation-gate | Phase 5 | Pending |
| NFR-cost-analysis-requirement | Phase 5 | Pending |
| SAFE-demo-only-phi-boundary | Phase 1 | Completed (evidence-based) |
| SAFE-rbac-boundary-integrity | Phase 4 | Pending |
| SAFE-canonical-markdown-governance | Phase 6 | Pending |
