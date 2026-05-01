# Phase 1 AI Integration Execution Plan

## Objective
Complete the remaining Phase 1 AI deliverables by finalizing the AI integration plan and implementation-intent architecture, while preserving evidence links for already-completed deployment/privacy controls.

## Non-Goals
- No OpenEMR redeploy or topology rebuild.
- No MariaDB networking changes.
- No new Phase 2+ RBAC/runtime implementation work.

## Scope Anchors
- Pending: `REQ-delivery-foundation-gates` (AI portion), `REQ-ai-integration-plan`, `REQ-ai-architecture-file`
- Evidence linkage only: `REQ-deployment-smoke-suite`, `NFR-private-network-topology`, `NFR-no-public-db-surface`, `SAFE-demo-only-phi-boundary`
- Existing artifact to finalize (not recreate): `.planning/AI-ARCHITECTURE.md`

## Execution Order (1-2 Day Cadence)
1. **Day 1 AM**: Baseline review + gap list against requirements.
2. **Day 1 PM**: Finalize `.planning/AI-ARCHITECTURE.md` content and traceability sections.
3. **Day 2 AM**: Build/update evidence linkage appendix and verification checklist.
4. **Day 2 PM**: Run final gate review and mark Phase 1 AI scope exit status.

## Work Breakdown

### Task 1 - Requirement-to-Artifact Gap Review
**Action**
- Compare `ROADMAP.md`, `REQUIREMENTS.md`, and `.planning/AI-ARCHITECTURE.md` line-by-line for Phase 1 AI scope.
- Produce a compact gap list (missing sections, weak requirement traceability, missing evidence references).

**Acceptance Criteria**
- Every pending requirement has an explicit destination section in `.planning/AI-ARCHITECTURE.md` or this execution plan.
- Gap list is actionable and limited to Phase 1 AI scope.

### Task 2 - Finalize `.planning/AI-ARCHITECTURE.md`
**Action**
- Edit and finalize existing `.planning/AI-ARCHITECTURE.md` to explicitly cover:
  - AI integration intent and trust boundaries
  - Delivery-gate alignment for AI portion of `REQ-delivery-foundation-gates`
  - Requirement ID traceability (`REQ-ai-integration-plan`, `REQ-ai-architecture-file`)
  - Demo-only PHI boundary language consistency

**Acceptance Criteria**
- `.planning/AI-ARCHITECTURE.md` remains the canonical implementation-intent file.
- Requirement IDs are explicitly mapped in-file.
- No section implies EMR redeployment is required.

### Task 3 - Evidence Linkage Consolidation (Already-Completed Controls)
**Action**
- Add or update a concise evidence linkage section (in `.planning/AI-ARCHITECTURE.md` or a linked checklist section in this plan) with pointers to proof artifacts for:
  - `REQ-deployment-smoke-suite`
  - `NFR-private-network-topology`
  - `NFR-no-public-db-surface`
  - `SAFE-demo-only-phi-boundary`
- Use existing docs as source of truth (`ARCHITECTURE.md`, `AUDIT.md`, `USERS.md`, deployment docs).

**Acceptance Criteria**
- Each listed ID has at least one evidence pointer and status (`Satisfied`, `Pending`, or `Needs refresh`).
- Evidence linkage distinguishes "already implemented" vs "AI documentation finalization."

### Task 4 - Final Verification and Phase 1 AI Exit Check
**Action**
- Run a final checklist pass to confirm all pending AI deliverables are complete and evidence links are present.
- Record a short execution note with completion status and any carry-over items (if any) for Phase 2.

**Acceptance Criteria**
- All pending Phase 1 AI requirements are marked complete or explicitly blocked with reason.
- Exit mapping table (below) is fully populated with status and artifact location.

## Verification Checklist and Evidence Artifacts
- [x] `.planning/AI-ARCHITECTURE.md` updated and finalized (not recreated).
- [x] Requirement traceability section includes:
  - [x] `REQ-delivery-foundation-gates` (AI portion)
  - [x] `REQ-ai-integration-plan`
  - [x] `REQ-ai-architecture-file`
- [x] Evidence linkage section includes:
  - [x] `REQ-deployment-smoke-suite`
  - [x] `NFR-private-network-topology`
  - [x] `NFR-no-public-db-surface`
  - [x] `SAFE-demo-only-phi-boundary`
- [x] Cross-reference validation completed against:
  - `ARCHITECTURE.md`
  - `AUDIT.md`
  - `USERS.md`
  - `.planning/ROADMAP.md`
  - `.planning/REQUIREMENTS.md`

## Risks and Mitigations
- **Risk: Scope creep into deployment reruns**
  - **Mitigation:** Enforce non-goal gate: no EMR/MariaDB redeploy tasks accepted in this phase close-out.
- **Risk: Requirement IDs marked complete without proof links**
  - **Mitigation:** Require evidence pointer per ID before status is set to complete.
- **Risk: Drift between AI architecture narrative and roadmap requirements**
  - **Mitigation:** Final verification pass must include explicit ID-to-section cross-check.
- **Risk: Ambiguous "demo-only" safety boundary language**
  - **Mitigation:** Normalize wording to match `SAFE-demo-only-phi-boundary` across artifacts.

## Exit Criteria Mapping (Phase 1)

| Requirement ID | Exit Condition | Evidence Artifact(s) | Final Status |
|---|---|---|---|
| `REQ-delivery-foundation-gates` (AI portion) | AI gating intent and integration constraints explicitly documented | `.planning/AI-ARCHITECTURE.md`, `.planning/ROADMAP.md` | Completed |
| `REQ-ai-integration-plan` | Explicit AI integration execution intent and constraints documented | `.planning/AI-ARCHITECTURE.md`, this plan | Completed |
| `REQ-ai-architecture-file` | Existing `.planning/AI-ARCHITECTURE.md` finalized as canonical artifact | `.planning/AI-ARCHITECTURE.md` | Completed |
| `REQ-deployment-smoke-suite` | Evidence link present (no re-execution required) | `ARCHITECTURE.md`, `AUDIT.md`, deploy docs | Linked |
| `NFR-private-network-topology` | Evidence link confirms private `.internal` topology | `ARCHITECTURE.md`, deploy docs | Linked |
| `NFR-no-public-db-surface` | Evidence link confirms no public DB endpoint | `ARCHITECTURE.md`, deploy docs | Linked |
| `SAFE-demo-only-phi-boundary` | Evidence link and consistent warning language present | `AUDIT.md`, `.planning/AI-ARCHITECTURE.md` | Linked |

## Immediate Next Action
Phase 1 AI closeout is complete. Proceed to `/gsd-plan-phase 2` for RBAC enforcement planning.
