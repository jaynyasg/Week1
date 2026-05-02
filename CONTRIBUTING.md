# Contributing

Treat markdown under `.planning/` as the authoritative source for requirements, decisions, and roadmap state. Exported Word copies or external documents are supplementary; if they disagree with `.planning/`, prefer the markdown and reconcile deliberately.

## Where to look

- [.planning/ROADMAP.md](.planning/ROADMAP.md)
- [.planning/STATE.md](.planning/STATE.md)
- [.planning/REQ-TEST-TRACEABILITY.md](.planning/REQ-TEST-TRACEABILITY.md)
- [.planning/FORK-CHECKLIST.md](.planning/FORK-CHECKLIST.md)
- [MAINTAINERS.md](MAINTAINERS.md)
- [.planning/eval-artifacts/README.md](.planning/eval-artifacts/README.md)
- [deploy/docs/operator-runbook.md](deploy/docs/operator-runbook.md) (operator triage)

Run the automated test suites from the repository root:

```text
python -m pytest agent/tests deploy/tests -q
```

Faster local loop (skips tests marked `@pytest.mark.eval`; optional gates may still skip on their own):

```text
python -m pytest agent/tests deploy/tests -q -m "not eval"
```

Optionally run lint on the agent package:

```text
python -m ruff check agent
```

Optional Git hooks: install with `pip install pre-commit && pre-commit install` to run `.pre-commit-config.yaml` (e.g. Ruff on `agent/`) before commit.

Makefile shortcuts: `make doctor` (Python/pytest versions + live-test env flags), `make pytest-fast` (excludes `@pytest.mark.eval`), `make openapi-check` (OpenAPI contract test), `make validate-fixtures` (full FK scan on `fixtures/sample-patients/*.csv`). On Windows without `make`, use `pwsh scripts/doctor.ps1`. Maintainer placeholders: [`MAINTAINERS.md`](MAINTAINERS.md).

Do not commit secrets. Keep credentials and environment-specific values in a local `.env` file (ignored by git), following `.env.example` where provided.

When you edit planning documents, preserve existing requirement and ADR-style identifiers (for example `REQ-*`, `NFR-*`, `SAFE-*`). Do not silently rewrite or remove text that records a locked decision; note conflicts explicitly and update through the project’s governance path instead.
