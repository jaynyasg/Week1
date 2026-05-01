# Fork / deployed-stack checklist

Use this when moving from **Week1 scaffold** to an **OpenEMR fork** or production-shaped deployment. Items reference `.planning/ROADMAP.md` gap tables and `PROJECT.md` fork guidance.

- [ ] **FHIR or clinical retrieve** — Session-scoped reads with RBAC; tests prove role boundaries against real data paths (`REQ-agent-requirements-coverage`).
- [ ] **LLM generate** — Model routing, prompts, timeouts, secrets per environment; no dev-only shortcuts on PHI hosts.
- [ ] **Programmatic verify** — Grounding against retrieved facts; bounded retries aligned with `MAX_VERIFY_RETRIES` / architecture.
- [ ] **SC3** — Record-backed source attribution and verification-limit notes in response artifacts (not scaffold-only).
- [ ] **`/agent/chat` hardening** — Rate limits, body limits, health/metrics as required; Apache or gateway alignment for embedded UI.
- [ ] **Phase 4 live** — `Observation.category` / labs–vitals validation where applicable; dashboards or saved queries for `event_type` triage.
- [ ] **Phase 5 gates** — Latency and cost evidence at checkpoints; store summaries under `.planning/eval-artifacts/` (see template there).
- [ ] **Phase 6** — External Word or PDF exports reconciled or marked non-authoritative per `WORD-INVENTORY.md`.
