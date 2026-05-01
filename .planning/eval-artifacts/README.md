# Eval artifacts

This directory holds checkpoint-ready evaluation outputs: latency summaries, cost notes, manual review verdicts, and similar evidence that reviewers can open without unpacking large payloads. Prefer small text summaries and structured files over large binaries by default.

**Suggested naming**: `YYYY-MM-DD-<checkpoint>-<topic>.md` or `YYYY-MM-DD-<checkpoint>-<topic>.json` so runs sort chronologically and tie to milestones or checkpoints.

Continuous integration stays fast by design. Heavy or expensive evaluations belong in local runs or scheduled pipelines that opt in through environment gates and quotas, rather than blocking every merge job.
