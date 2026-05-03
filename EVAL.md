# Behavioral evaluation tests (`agent/tests/eval/`)

**Purpose:** Offline behavioral coverage for **LLM tool dispatch**, **RBAC refusals**, **patient scope**, **OpenAI tool-loop shape** (mocked API; no network), and **CSV fixture cohort** smoke checks. These are **pytest** tests, many marked `@pytest.mark.llm_eval` for selective runs.

**Last updated:** 2026-05-03

---

## How to run

```bash
# Full eval package (typical: 74 tests)
python -m pytest agent/tests/eval/ -q

# LLM-eval subset only
python -m pytest agent/tests/eval/ -q -m llm_eval
```

CI may run these as part of the broader `agent/tests` tree. See [`README.md`](README.md) for full-suite commands.

---

## Inventory: **53** “core matrix” tests

These prove the **contract** the model relies on: schemas, RBAC matrix, tool-loop behavior, and fixture data.

| Module | Count | What it proves |
| --- | --- | --- |
| [`test_tool_dispatch_matrix.py`](agent/tests/eval/test_tool_dispatch_matrix.py) | 36 | **PHYSICIAN / NURSE / ADMIN** × five clinical functions (`get_patient_demographics`, `list_active_medications`, `list_recent_laboratory_results`, `list_recent_vital_signs`, `list_allergies`): allowed vs **ToolRefusal**; unknown function; bad JSON; **patient_id** scope mismatch vs session; missing patient semantics; OpenAI schema count (5 tools) and required `patient_id`; unknown/lowercase roles rejected; idempotent repeat calls. |
| [`test_openai_tool_loop_mocked.py`](agent/tests/eval/test_openai_tool_loop_mocked.py) | 14 | Mocked **multi-round** tool loop: no-tool path, single tool, parallel tools, **RBAC recovery** after nurse labs refusal, max rounds, empty final message error, second round after refusal, message serialization, per-tool payload shapes, wrong `patient_id` in tool args, transcript hygiene. |
| [`test_csv_cohort_smoke.py`](agent/tests/eval/test_csv_cohort_smoke.py) | 3 | Synthea-style **CSV fixtures** under [`fixtures/sample-patients/`](fixtures/sample-patients/) load; seed patient row present; medications non-empty for demo UUID `f1aa52b9-aded-3188-9386-012244805ebf`. |

**Total:** 36 + 14 + 3 = **53**.

---

## Inventory: **21** edge-case / failure-mode tests

[`test_edge_cases_and_failure_modes.py`](agent/tests/eval/test_edge_cases_and_failure_modes.py) adds **21** tests for:

- Multi-tool sequences and **`source`** key (`csv` vs `openemr_fhir` when FHIR env incomplete).
- RBAC passes for nurse/admin on allowed tools; **all five** physician tools emit `rbac_tool`.
- Empty / whitespace **`patient_id`** in tool arguments → scope violation (not silent success).
- **Missing cohort data:** zero meds/allergies as empty counts; unknown patient demographics → not found.
- **Malformed arguments:** extra keys ignored; deeply nested junk does not crash.
- **Unknown function** path returns structured error (distinct from RBAC refusal).
- **`OpenEMRNotConfigured`:** env validation; FHIR code path falls back to CSV when secrets absent.
- **Concurrent** physician + admin dispatch (no shared-state crash).

---

## Relationship to PRD “eight tools”

[`USERS.md`](USERS.md) Part 2 defines **eight** logical agent tools (includes `problem_list`, `visit_notes`, `schedule`). The **current** OpenAI function surface in [`agent/tools/dispatch.py`](agent/tools/dispatch.py) exposes **five** clinical read tools plus RBAC mapping to those logical ids. The remaining tools are **fork / roadmap** work; evals intentionally focus on what the repo **ships** today.

---

## Traceability

- Clinician demo prompts: [`deploy/CLINICIAN-WORKFLOWS.md`](deploy/CLINICIAN-WORKFLOWS.md)
- RBAC implementation: [`agent/access/rbac.py`](agent/access/rbac.py)
- Project narrative: [`PROJECT-SHOWCASE.md`](PROJECT-SHOWCASE.md) · AI plan: [`.planning/AI-ARCHITECTURE.md`](.planning/AI-ARCHITECTURE.md)
