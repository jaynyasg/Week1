# Pre-Search Checklist → evidence matrix (repo scope)

This matrix maps checklist-style concerns to concrete evidence in this repository. Rows without a definitive PRD or appendix locator use short labels. Status reflects what this repo proves today; items that depend on an OpenEMR fork or full production stack are marked **N/A until fork** where appropriate.

| Checklist item (or ID) | Evidence location (file path) | Status | Notes |
| --- | --- | --- | --- |
| Canonical requirements / roadmap | `.planning/ROADMAP.md` | Pass | Phases, REQ/NFR/SAFE IDs, and gap commentary live here—not in Word exports alone. |
| PRD ingestion / classification | `.planning/ingest/classifications/PRD-AgentForge-Clinical-CoPilot-Requirements.classification.json` | Partial | Classification artifact; full PRD text may live outside the repo. |
| RBAC enforcement (agent runtime) | `agent/tests/integration/test_tool_route_rbac.py`, `agent/tests/unit/test_rbac_matrix.py`, `agent/tests/unit/test_rbac_matrix_properties.py` | Pass | Matrix and deny paths covered in tests; production OpenEMR session shapes may differ in fork. |
| Source attribution (clinical responses) | `.planning/ROADMAP.md` (Phase 3, SC3 / gap table), `agent/runtime/rgv_pipeline.py` (contract fields) | Partial | Scaffold exposes verification and artifact fields; record-backed attribution in responses remains fork work per roadmap. |
| Verification failures and graceful degradation | `agent/tests/unit/test_rgv_pipeline.py`, `agent/tests/integration/test_chat_route.py` | Pass | Bounded retry and explicit unverified exits tested in scaffold; domain verifier depth is fork-aligned. |
| Latency / performance validation | `.planning/ROADMAP.md` (Phase 5), `agent/tests/integration/test_latency_gate_optional.py` (`RUN_LATENCY_GATE=1`), `agent/tests/integration/test_agent_limits_and_observability.py` | Partial | Coarse TestClient wall-time gate for scaffold chat; full SLO proofs and checkpoints belong in eval artifacts or scheduled pipelines. |
| Cost envelope / evaluation gates | `.planning/ROADMAP.md` (Phase 5), `.planning/eval-artifacts/README.md` | N/A until fork | Capture cost summaries under `.planning/eval-artifacts/`; automated cost gates not asserted in default CI paths here. |
| Deployment safety / operator context | `deploy/docs/safe-rollout.md`, `deploy/docs/operator-runbook.md`, `deploy/docs/security-audits.md` | Partial | Operational guidance exists; PHI boundaries and tenant-specific controls need fork-specific assurance. |
