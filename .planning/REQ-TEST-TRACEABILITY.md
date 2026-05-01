# Requirement → test traceability (repo)

Lightweight map from `.planning/REQUIREMENTS.md` IDs to **automated evidence** in this repository. Fork-only or manual verification stays out of this table.

| Requirement ID | Primary test paths (non-exhaustive) |
| --- | --- |
| `REQ-openemr-session-validation` | `agent/tests/unit/test_openemr_auth.py`, `agent/tests/integration/test_http_deps.py`, `agent/tests/integration/test_live_openemr_optional.py` (gated) |
| `REQ-rbac-agent-layer` / `REQ-rbac-tool-matrix` / `REQ-rbac-deny-path` | `agent/tests/unit/test_rbac_matrix.py`, `agent/tests/unit/test_rbac_matrix_properties.py`, `agent/tests/integration/test_tool_route_rbac.py` |
| `REQ-retrieve-generate-verify-loop` / `REQ-verification-layer-contracts` (scaffold) | `agent/tests/unit/test_rgv_pipeline.py`, `agent/tests/unit/test_scaffold_response_contract.py`, `agent/tests/integration/test_chat_route.py` |
| `REQ-multi-turn-usecase-behavior` (scaffold) | `agent/tests/integration/test_chat_route.py` |
| `REQ-deployment-smoke-suite` | `deploy/tests/integration/test_deployment.py` |
| `NFR-observability-coverage` / `NFR-observability-minimum-questions` (scaffold) | `agent/tests/unit/test_events.py`, `agent/tests/unit/test_observability_log_minimum_questions.py`, `agent/tests/integration/test_http_logging_observability.py`, `agent/tests/integration/test_openemr_base_url_misconfiguration.py`, `agent/tests/integration/test_dependency_log_contracts.py` |
| OpenAPI / route stability (engineering) | `agent/tests/unit/test_openapi_contract.py` |
| Deploy docs link integrity | `deploy/tests/test_docs_internal_links.py` |
| `NFR-eval-suite-unauthorized-access` (partial) | RBAC tests above; `agent/tests/integration/test_agent_limits_and_observability.py` |
| `NFR-latency-validation-gate` (coarse, gated) | `agent/tests/integration/test_latency_gate_optional.py` (`RUN_LATENCY_GATE=1`, `@pytest.mark.eval`) |
| `SAFE-demo-only-phi-boundary` | Documented in deploy docs; no single pytest ID |
| `SAFE-rbac-boundary-integrity` | RBAC matrix tests; live `Observation.category` validation remains fork work per ROADMAP |

Update this table when you add tests that close new requirement IDs.
