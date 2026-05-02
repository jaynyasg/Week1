# Eval snapshot — submission prep (2026-05-01)

**Purpose:** Reproducible **evidence pointer** for Gauntlet “eval dataset / results.” Continuous numbers drift—refresh before final submission.

## Commands (from repo root)

```bash
python -m pytest agent/tests deploy/tests -q
python -m pytest agent/tests deploy/tests -q -m "not eval"
```

Optional gates (require env / creds):

```bash
# Live OpenEMR + optional deployed agent — see .env.example
set RUN_LIVE_OPENEMR_E2E=1
python -m pytest agent/tests/integration/test_live_openemr_optional.py -q
```

Lint (matches CI):

```bash
python -m ruff check agent
```

## Last recorded full offline run (developer machine)

| Metric | Value |
| --- | --- |
| **Passed** | ~163 |
| **Skipped** | ~15 |
| **Notes** | Skips include live OpenEMR, optional eval/latency gates |

Replace this table with your **actual** `pytest` summary line before recording the demo.

## What the suite covers (high level)

- **Unit:** RGV ordering/retry, RBAC matrix, HTTP deps, OpenAPI contract, chat schemas, OpenEMR fetch transport mocks.
- **Integration:** `POST /agent/chat` auth paths, multi-turn history, observability log fields, rate limits (when env set), OpenEMR base URL misconfiguration.
- **Deploy:** Fly manifest / offline deploy tests under `deploy/tests/`.

## Traceability

Requirement ↔ test mapping: [`.planning/REQ-TEST-TRACEABILITY.md`](../REQ-TEST-TRACEABILITY.md).
