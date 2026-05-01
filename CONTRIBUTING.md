# Contributing

Treat markdown under `.planning/` as the authoritative source for requirements, decisions, and roadmap state. Exported Word copies or external documents are supplementary; if they disagree with `.planning/`, prefer the markdown and reconcile deliberately.

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

Do not commit secrets. Keep credentials and environment-specific values in a local `.env` file (ignored by git), following `.env.example` where provided.

When you edit planning documents, preserve existing requirement and ADR-style identifiers (for example `REQ-*`, `NFR-*`, `SAFE-*`). Do not silently rewrite or remove text that records a locked decision; note conflicts explicitly and update through the project’s governance path instead.
