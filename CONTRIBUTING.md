# Contributing

Treat markdown under `.planning/` as the authoritative source for requirements, decisions, and roadmap state. Exported Word copies or external documents are supplementary; if they disagree with `.planning/`, prefer the markdown and reconcile deliberately.

Run the automated test suites from the repository root:

```text
python -m pytest agent/tests deploy/tests -q
```

Optionally run lint on the agent package:

```text
python -m ruff check agent
```

Do not commit secrets. Keep credentials and environment-specific values in a local `.env` file (ignored by git), following `.env.example` where provided.

When you edit planning documents, preserve existing requirement and ADR-style identifiers (for example `REQ-*`, `NFR-*`, `SAFE-*`). Do not silently rewrite or remove text that records a locked decision; note conflicts explicitly and update through the project’s governance path instead.
