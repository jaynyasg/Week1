# Phase 2 Execution Plan - RBAC Enforcement and Test Matrix

## Objective
Implement and verify runtime RBAC enforcement so every agent tool call is authorized against the 8-tool role matrix, with explicit deny/refusal behavior and auditable logging.

## Non-Goals
- No retrieve-generate-verify flow redesign (Phase 3 scope).
- No new observability platform work beyond RBAC deny logging checks (Phase 4 scope).
- No latency/performance benchmarking expansion beyond RBAC-path test runtime sanity (Phase 5 scope).
- No documentation governance/Word reconciliation work (Phase 6 scope).

## Source of Truth
- `USERS.md` (normative role/tool matrix, deny behavior).
- `ARCHITECTURE.md` (auth/session validation flow, retrieve-node RBAC placement).
- `AUDIT.md` (risk context: category boundary integrity, refusal logging, implementation pending state).
- `.planning/AI-ARCHITECTURE.md` (trust boundaries, required RBAC deny observability events).
- `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` (Phase 2 goal + requirement IDs).

## Task Breakdown With Acceptance Criteria

### Task Group 1 - Runtime Surface Discovery and Contract Freeze
**Intent**: Avoid path assumptions and pin exact implementation locations before code changes.

1) **Discover auth/session validation entrypoints**
- **Action**: Locate the middleware/router path where OpenEMR session tokens are validated via `/api/user` and identify the first point where role context is attached to agent requests.
- **Acceptance Criteria**:
  - A concrete file/function map exists for token validation and role injection.
  - The mapped flow matches `ARCHITECTURE.md` auth boundary (`Auth Middleware -> /api/user`).
  - Unknown/missing role behavior is explicitly documented as deny by default.

2) **Discover retrieve-node tool dispatch and RBAC hook point**
- **Action**: Locate the retrieve/tool-dispatch execution path and identify exact hook(s) where `enforce(role, tool)` must execute before tool invocation.
- **Acceptance Criteria**:
  - A concrete dispatch path map exists from request -> retrieve node -> tool call.
  - RBAC enforcement point is before any tool execution (meets `REQ-rbac-agent-layer`).
  - Tool canonical names in runtime are mapped to matrix names from `USERS.md`.

3) **Freeze role/tool matrix contract in code-adjacent form**
- **Action**: Define an immutable role-to-tool contract based on `USERS.md`:
  - `PHYSICIAN`: all 8 tools.
  - `NURSE`: `demographics`, `medications`, `vitals`, `allergies`, `schedule`.
  - `ADMIN`: `demographics`, `schedule` only.
- **Acceptance Criteria**:
  - Contract includes all 8 tools and all 3 roles.
  - Unknown role and unknown tool paths are represented as deny.
  - Contract naming is compatible with runtime tool identifiers.

---

### Task Group 2 - RBAC Enforcement Implementation
**Intent**: Enforce policy in the agent runtime path for every tool call.

1) **Implement role normalization and guardrail defaults**
- **Action**: Add/confirm role normalization from OpenEMR role strings to `{PHYSICIAN, NURSE, ADMIN}` with deny-default for unknown/unmapped values.
- **Acceptance Criteria**:
  - Unmapped roles cannot access any clinical tools.
  - Runtime path cannot proceed to tool dispatch without a resolved role outcome.

2) **Implement per-tool enforcement at dispatch time**
- **Action**: Add enforcement call in retrieve/dispatch layer that checks every candidate tool against allowed set before invocation; disallowed tool calls are refused, not silently filtered.
- **Acceptance Criteria**:
  - All tool calls pass through a single enforce/check function (or equivalent invariant).
  - Disallowed tools are blocked prior to client/API call execution.
  - Composite flows cannot bypass disallowed tools through alternate aliases.

3) **Implement explicit refusal payload and control flow**
- **Action**: Return refusal responses that include both role and blocked tool, aligned with `USERS.md` deny behavior.
- **Acceptance Criteria**:
  - Refusal messaging contains role + tool in deterministic format.
  - Denial does not leak partial clinical content from blocked tool paths.
  - Multiple denied tools produce predictable aggregate refusal behavior (single combined refusal or deterministic per-tool refusal).

---

### Task Group 3 - Role/Tool Matrix Validation Strategy
**Intent**: Prove matrix correctness and prevent regressions.

1) **Build matrix-driven unit tests**
- **Action**: Create parameterized unit tests from a single canonical matrix fixture that covers all `(role, tool)` pairs plus unknown role/tool cases.
- **Acceptance Criteria**:
  - Test matrix covers 3 roles x 8 tools + unknown role + unknown tool.
  - Expected allow/deny outcomes exactly match `USERS.md`.
  - Any matrix drift fails tests with clear diff output.

2) **Add agent-layer integration tests on real dispatch path**
- **Action**: Add integration tests that pass through auth/session validation and retrieve dispatch to assert enforcement at runtime, not only in pure unit logic.
- **Acceptance Criteria**:
  - Invalid/expired/no-session requests are rejected pre-tool execution (`REQ-openemr-session-validation`).
  - Allowed combinations execute; denied combinations refuse.
  - At least one ADMIN clinical-tool deny case and one NURSE labs deny case are covered.

3) **Add deny-path and side-channel negative tests**
- **Action**: Add negative tests proving denied calls do not return blocked-tool data, and that refusal payload remains explicit.
- **Acceptance Criteria**:
  - Denied responses contain role+tool and no clinical payload from blocked tool.
  - Tool client mocks/spies confirm blocked tools were never executed.
  - Unknown role/tool negative cases are covered.

---

### Task Group 4 - Logging and Refusal Behavior Checks
**Intent**: Ensure denials are auditable and safe.

1) **Validate deny event logging fields**
- **Action**: Verify deny logs include role, tool, and hashed identifiers per policy; verify no raw PHI fields are emitted on deny paths.
- **Acceptance Criteria**:
  - Deny events are emitted for every refusal case.
  - Log payload has required fields and uses hashed IDs.
  - No raw patient identifiers or note/lab payloads appear in deny logs.

2) **Verify refusal behavior consistency across endpoints**
- **Action**: Validate refusal behavior for each relevant endpoint path that can trigger tools (`/chat`, summary route if present, and any equivalent retrieval entrypoint discovered in Task Group 1).
- **Acceptance Criteria**:
  - Refusal format is consistent across entrypoints.
  - Deny behavior does not vary by endpoint in ways that leak scope.
  - Endpoint-level tests exist for at least one denied matrix case each.

## Test Plan (Unit + Integration + Negative)

### Unit Tests
- RBAC contract tests for role normalization and allowed-set derivation.
- Full role/tool matrix parameterized tests (allow + deny assertions).
- Refusal formatter tests (role+tool presence, deterministic wording).

### Integration Tests
- Session validation gate tests: invalid/missing OpenEMR session rejected before dispatch.
- End-to-end dispatch tests: auth -> role injection -> RBAC check -> tool invocation/refusal.
- Endpoint consistency tests for runtime refusal behavior.

### Negative Tests
- Unknown role defaults to deny.
- Unknown tool defaults to deny.
- NURSE denied on `labs` and `visit_notes`.
- ADMIN denied on all clinical tools (`problem_list`, `medications`, `labs`, `vitals`, `allergies`, `visit_notes`).
- Side-channel protection: denied paths do not call tool clients and do not return partial tool data.

## Logging / Refusal Behavior Validation Strategy
- Validate refusal response contract includes `role` and `tool` in all deny cases.
- Validate deny log records are generated in same request lifecycle as refusal.
- Validate logs include only permitted identifiers (hashed), with no PHI payload leakage.
- Validate deny events are queryable by role/tool for auditability.

## Risks and Mitigations
- **Risk: Runtime alias mismatch between matrix tool names and dispatch tool names**
  - **Mitigation**: Add explicit tool-name mapping layer and enforce one canonical enum in tests.
- **Risk: Enforcement accidentally occurs after partial tool execution**
  - **Mitigation**: Add integration assertions that blocked tool client methods are never invoked.
- **Risk: Session validation bypass in alternative endpoint path**
  - **Mitigation**: Discovery-first endpoint inventory plus per-endpoint deny/invalidation tests.
- **Risk: Refusal logs leak sensitive data**
  - **Mitigation**: Add structured log-schema tests and deny-path log snapshot checks.
- **Risk: Matrix drift between docs and implementation**
  - **Mitigation**: Generate matrix fixture directly from one canonical source in code and fail tests on mismatch.

## Exit Criteria Mapping (Requirements -> Done Definition)

| Requirement ID | Exit Condition | Evidence |
|---|---|---|
| `REQ-openemr-session-validation` | Requests lacking valid OpenEMR session context are rejected before tool execution. | Integration tests proving pre-dispatch rejection; auth-path verification notes. |
| `REQ-rbac-agent-layer` | RBAC is enforced in agent retrieve/dispatch path for every tool call, not UI-only. | Dispatch-path integration tests + code-level invariant checks. |
| `REQ-rbac-tool-matrix` | Runtime behavior matches 8-tool role matrix exactly; ADMIN limited to demographics + schedule. | Parameterized matrix unit tests and targeted integration cases. |
| `REQ-rbac-deny-path` | Denied calls return explicit role+tool refusals and produce auditable safe logs without leakage. | Negative tests + logging schema/assertion tests + refusal contract tests. |

## Suggested Execution Sequence (1-3 Days)
- **Day 1**: Task Group 1 (discovery + contract freeze) and start Task Group 2 (guard defaults + enforcement hook).
- **Day 2**: Complete Task Group 2 and implement Task Group 3 unit/integration matrix tests.
- **Day 3**: Complete Task Group 4 logging/refusal checks, run full RBAC test suite, and finalize requirement evidence notes.

## Main Deliverable Groups
1. Runtime RBAC enforcement wired at agent tool-dispatch layer.
2. Matrix-based unit/integration/negative tests with deny-path coverage.
3. Refusal and logging behavior validated for auditable, non-leaky denials.
