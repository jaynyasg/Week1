# Document control — Word exports vs repository markdown

**Authority for implementation in this repository:** [`USERS.md`](USERS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`AUDIT.md`](AUDIT.md), [`EVAL.md`](EVAL.md), and [`PRD-AgentForge-Clinical-CoPilot-Requirements.md`](PRD-AgentForge-Clinical-CoPilot-Requirements.md) (PDF ingest summary).

External Word copies cited in the audit (**`Clinical_CoPilot_PRD.docx` v1.0**, **`Clinical_CoPilot_TaskList_v2.docx` v2.0** — see **AUD-012**, **AUD-013** in [`AUDIT.md`](AUDIT.md)) are **not authoritative** when they disagree with the markdown above (e.g. seven vs eight tools, nurse access to `labs`, PCP story numbering). **`USERS.md` Part 2** is the RBAC matrix of record.

**Practical rule:** Do not implement RBAC, tool lists, or API routes from Word task lists without diffing to this repository. If stakeholders need Word, re-export from markdown or mark documents **SUPERSEDED — see Week1 `USERS.md` / `ARCHITECTURE.md`**.

**Adds traceability for:** AUD-012, AUD-013 (governance closure at the source-of-truth level).
