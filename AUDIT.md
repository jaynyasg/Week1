# Clinical Co-Pilot — System Audit (AUDIT.md)

**AgentForge · Gauntlet AI**  
**Audit artifact version:** 1.3 · **Date:** May 3, 2026 *(status refresh; original review April 28, 2026)*  
**Sources reviewed:** `AF/architecture.md`, `AF/PRD.md` (v1.1), `AF/Tasks.md` (v2.1), `users.md` (RBAC — aligned with PRD Feature 8 as of v1.1), `Projects/AgentForge/Clinical_CoPilot_PRD.docx` (Word **v1.0**), `Projects/AgentForge/Clinical_CoPilot_TaskList_v2.docx` (Word **v2.0**)

---

## Executive summary (~500 words)

This audit reviews the Clinical Co-Pilot design as expressed in the Week 1 architecture narrative, **markdown** PRD **v1.1** (`AF/PRD.md`), the PR/task map **v2.1** (`AF/Tasks.md`), and `users.md` (RBAC tool matrix aligned with PRD Feature 8 as of audit v1.1). **Additionally**, two **Word** sources in `Projects/AgentForge/` were reviewed by extracting body text from the `.docx` packages: **`Clinical_CoPilot_PRD.docx` (dated Version 1.0)** and **`Clinical_CoPilot_TaskList_v2.docx` (Version 2.0)**. Those Word files are **not equivalent** to the markdown versions: they describe an **older / alternate baseline** (e.g. **10** MVP features vs **11** in v1.1, **seven** patient tools with **no vitals/labs split**, different **PCP story numbering**, generic RBAC without the **ADMIN tool matrix**, and different **LLM / HIPAA** framing). **For implementation and Gauntlet hard gates, treat `AF/PRD.md` v1.1 + `AF/Tasks.md` v2.1 as authoritative** unless product explicitly re-baselines the Word exports.

The intended system (per **v1.1 markdown + architecture**) is a FastAPI agent behind Nginx, validating OpenEMR session context (cookies and/or Bearer token), retrieving patient context through **eight** distinct logical tools (FHIR-first, REST where needed), running a retrieve → generate → verify loop, streaming to a **React/Vite** panel embedded in OpenEMR, and emitting PHI-safe logs plus Langfuse traces (target)—including explicit **`POST /flag`** audit events without re-generation.

The design is internally strong on several non-negotiable clinical-AI controls: session scoping to a single patient, programmatic verification (grounding plus domain rules), graceful degradation when the agent is down, and a stated refusal to persist conversation content to disk. The PRD’s MVP hard gates correctly force documentation, deployment, user modeling, architecture defense, and this audit before heavy implementation.

**Update (audit v1.3):** [`USERS.md`](USERS.md) / [`agent/access/rbac.py`](agent/access/rbac.py) + **[`EVAL.md`](EVAL.md)** implement PRD Feature 8 refusals in code (superseding “RBAC pending” language from v1.1).

**Update (AUD-003):** External **`AF/PRD.md` §2** may still say “seven” functions — the **in-repo** ingest PRD and **`USERS.md`** state **eight** tools with labs/vitals split; reconcile **`AF/`** copies when distributed.

Operational and data-quality dependencies: **FHIR latency** toward the five-second summary budget can be probed with [`scripts/benchmark_fhir_latency.py`](scripts/benchmark_fhir_latency.py) (**AUD-005** partial until p50/p95 are recorded). **`Observation.category`** integrity is **mitigated** in-agent by filtering each returned resource (**AUD-004**); **unlabeled** observations are omitted—fix imports for full charts. **Verification policy** for partial grounding is **documented for the scaffold**; full strip/withhold semantics remain fork work (**AUD-006**). **Langfuse** hosting posture remains an operator choice (**AUD-009**).

**Scope limitation (critical transparency):** The **2026-04-28** audit pass was **design- and document-level** for external `AF/` artifacts. The **2026-05-03** repository snapshot adds **runnable agent code** (FastAPI, RBAC, OpenEMR auth paths, FHIR client, behavioral evals—see §Update 2026-05-03 and Appendix C). Findings below remain **design truth statements**; **closure status** is tracked in §6 with **2026-05-03** remediation notes where the **Week1 repo** addresses them. Runtime security testing, PHI log sampling, and **published** FHIR latency tables are still **operator responsibilities** for production gates.

Overall readiness: **RBAC narrative is unified in `USERS.md` with the markdown PRD v1.1**; **tool-count language in external `AF/PRD.md` §2 should still be corrected where it says “seven”** (in-repo ingest PRD updated — **AUD-003** in this repo); **Word PRD v1.0 and Word TaskList v2.0 must not be treated as equivalent to markdown v1.1 / v2.1** — use **[`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md)** for authority (**AUD-012**, **AUD-013**); **AUD-005** needs **measured** p50/p95 (script provided); **AUD-006** fork policy for partial claims still open beyond scaffold documentation.

### Update 2026-05-03 (implementation evidence, not a re-audit)

Since audit **v1.2**, this repository gained **executable** (still demo-scoped) pieces that narrow—but do not fully close—earlier **“no code in scope”** caveats:

- **RBAC enforcement** in [`agent/access/rbac.py`](agent/access/rbac.py) with pytest coverage including [`agent/tests/eval/`](agent/tests/eval/) (**see [`EVAL.md`](EVAL.md)**).
- **OpenEMR auth** via **PHP session probe** + **Standard API Bearer** + optional **demo bypass** ([`agent/access/openemr_auth.py`](agent/access/openemr_auth.py), [`deploy/copilot_session_probe.php`](deploy/copilot_session_probe.php)).
- **Five** LLM-callable clinical tools (CSV + optional FHIR) ([`agent/tools/dispatch.py`](agent/tools/dispatch.py)).
- **FHIR Observation defense-in-depth:** category coding filter + `skipped_not_matching_category` ([`agent/tools/openemr_fhir.py`](agent/tools/openemr_fhir.py)) — **AUD-004 mitigated** (not eliminated: untagged data still omitted).
- **FHIR latency probe:** [`scripts/benchmark_fhir_latency.py`](scripts/benchmark_fhir_latency.py) — **AUD-005 partial** until results are recorded.
- **Document control:** [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md) — **AUD-012 / AUD-013 governance** closure for this repo.

Runtime security review, PHI log sampling, and **published** FHIR benchmark tables **still** require a controlled environment—this note does **not** replace those activities. See **§6 status (v1.3)** for closure codes (**Resolved / Mitigated / Partial / Open**).

---

## 1. Overview

| Item | Description |
|------|-------------|
| **Product** | Clinical Co-Pilot — OpenEMR-embedded, patient-scoped, record-grounded agent |
| **Audit purpose** | Satisfy PRD §7 hard gate (“AUDIT.md — security, performance, architecture, data quality, compliance”) and de-risk PRs #01–#15 |
| **Audit type** | Static review of authoritative specs and task plan; no live system test in this pass |
| **Audience** | Builders (PR owners), reviewers (Gauntlet submission), future security review |

---

## 2. Scope of audit

### 2.1 In scope

- Consistency across **architecture**, **PRD**, **Tasks**, **`users.md`**, and **Word exports** (`Clinical_CoPilot_PRD.docx`, `Clinical_CoPilot_TaskList_v2.docx`) vs markdown sources
- Security and compliance **intent** (auth passthrough, RBAC, logging, LLM data policy, session isolation)
- Performance **budgets and dependencies** as stated (FHIR parallel fetch, verification latency)
- Data-quality **requirements** for demo patients and FHIR Observation categorization
- Traceability from **Features / user stories** → **task PRs** → **test artifacts**

### 2.2 Out of scope (explicit limitations)

| Limitation | Impact |
|------------|--------|
| No **canonical** deployed OpenEMR + agent stack in every reviewer environment | Cannot validate TLS, **production** FHIR p95 for all readers. **Mitigation:** [`scripts/benchmark_fhir_latency.py`](scripts/benchmark_fhir_latency.py) when `OPENEMR_*` secrets are set. |
| **Historical (April 2026 snapshot):** no `rbac.py` in tree | **Superseded in Week1 repo:** [`agent/access/rbac.py`](agent/access/rbac.py) + eval coverage ([`EVAL.md`](EVAL.md)). |
| No live log / Langfuse sample review in this static pass | Cannot certify absence of raw PHI in sinks — operator security review still required. |
| No legal / BAA interpretation | Only policy alignment to PRD §1.4 demo-data assumption is assessed. |

### 2.3 Authoritative documentation (conflict resolution)

| Priority | Artifact | Role |
|----------|----------|------|
| **1 — Normative** | `AF/PRD.md` **v1.1** | Feature set, RBAC matrix (Feature 8), flagging (Feature 7), vitals/labs split, conversation data policy, MVP gates |
| **1 — Normative** | `AF/Tasks.md` **v2.1** | PR boundaries, file map, tests aligned to v1.1 |
| **2 — Reference** | `AF/architecture.md`, `users.md` | Architecture narrative and RBAC tool matrix (must stay consistent with **1**) |
| **3 — Historical / snapshot** | `Clinical_CoPilot_PRD.docx` **v1.0**, `Clinical_CoPilot_TaskList_v2.docx` **v2.0** | Useful for provenance; **do not implement from these alone** without reconciling to **1** (see **AUD-012**, **AUD-013**) |

---

## 3. Methodology

1. **Cross-walk:** Mapped PRD Features 1–11 to `AF/architecture.md` components and `AF/Tasks.md` PR boundaries.
2. **Word vs markdown reconciliation:** Extracted text from `Clinical_CoPilot_PRD.docx` and `Clinical_CoPilot_TaskList_v2.docx` (Office Open XML `word/document.xml`) and compared to `AF/PRD.md` / `AF/Tasks.md` for version drift, feature count, tool split, RBAC matrices, and API surface (e.g. `/flag`, `/summary` vs chart-load flows).
3. **Contradiction scan:** Compared normative statements (especially RBAC, tool count, admin role) across documents.
4. **Risk classification:** Assigned **severity** using the scale below; each finding has a **unique ID** and **actionable remediation**.
5. **Gate linkage:** Where Tasks.md defines PR acceptance checks, findings reference those checks as verification.

### Severity scale

| Level | Meaning |
|-------|---------|
| **Critical** | Would violate PRD hard gate, cause unauthorized disclosure, or create misleading clinical output if shipped as-is |
| **High** | Likely implementation bug, failed eval category, or compliance gap without further design fix |
| **Medium** | Degrades operability, observability, or maintainability; fix before or during relevant PR |
| **Low** | Documentation clarity, naming, or future tech debt |

---

## 4. Findings (core)

| ID | Area | Severity | Finding | Evidence / conflict |
|----|------|----------|---------|----------------------|
| **AUD-001** | Security / RBAC | **Critical** | **`users.md` contradicted PRD Feature 8 on `ADMIN` permissions** (historical). **Resolved (docs):** `users.md` now matches PRD — ADMIN may use **`demographics` + `schedule` only**; clinical tools must refuse with role + tool named. | PRD §4 Feature 8; PRD §2 Definitions; `users.md` (post–v1.1) |
| **AUD-002** | Security / RBAC | **High** | **`users.md` nurse “write notes” did not match PRD MVP agent tools** (historical). **Resolved (docs):** nurse flow is **subset of eight read tools** only; explicit note that write paths are out of Feature 8 unless PRD is amended. | PRD §4 Feature 8; PRD §3.3; `users.md` (post–v1.1) |
| **AUD-003** | Documentation | **Medium** | **External `AF/PRD.md` may still say “7 patient context functions”** while Feature 4 defines eight tools. **Resolved (in-repo):** [`PRD-AgentForge-Clinical-CoPilot-Requirements.md`](PRD-AgentForge-Clinical-CoPilot-Requirements.md) + [`USERS.md`](USERS.md) state eight tools with labs/vitals split. Reconcile **AF/** copy if used. | PRD §2 “Tool call”; PRD §4 Feature 4 |
| **AUD-004** | Data quality | **High** | **RBAC boundary for nurses depends on correct FHIR `Observation.category` tagging.** **Mitigated (agent):** [`agent/tools/openemr_fhir.py`](agent/tools/openemr_fhir.py) drops observations whose `category` coding does not match the requested tool (`laboratory` vs `vital-signs`); `skipped_not_matching_category` surfaces miscategorized rows. **Residual:** uncategorized observations are omitted—data import must tag categories for full charts. | PRD §3.3 NR-01; unit tests `test_observation_category_filter.py` |
| **AUD-005** | Performance | **High** | **End-to-end pre-visit summary (≤5s) is unproven** against real OpenEMR FHIR latency. **Partial remediation:** operator timing via [`scripts/benchmark_fhir_latency.py`](scripts/benchmark_fhir_latency.py); **residual** = paste p50/p95 into next audit revision. | PRD §1.2 metrics; PRD §8 FHIR latency question |
| **AUD-006** | Safety / UX | **Medium** | **Verification threshold for partial unverifiable claims** (“strip + count” vs “withhold all”). **Scaffold documented** in [`ARCHITECTURE.md`](ARCHITECTURE.md) (verified flag + bounded retry); **fork/ADR** still owns final strip/withhold policy. | PRD §6 Feature 6; PRD §8 open question |
| **AUD-007** | Security | **Medium** | **Session isolation** — **Resolved (scaffold):** stateless FastAPI; role from OpenEMR auth; `patient_id` + `X-Clinical-Session-Id` per request (see [`ARCHITECTURE.md`](ARCHITECTURE.md)). **Fork:** optional Redis session store + TTL if PRD requires stricter replay semantics. | PRD §8; [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **AUD-008** | Compliance | **Medium** | **Anthropic usage without BAA** is acceptable **only** under demo-data policy; any drift to real PHI invalidates the assumption. Must stay visible in architecture + runbooks. | PRD §1.4; PRD §5 stack pitfalls |
| **AUD-009** | Observability | **Low** | **Langfuse “self-hosted” vs cloud** choice affects compliance narrative; PRD asks for explicit documentation before queries. **Partial:** scaffold logs documented in [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md). | PRD §8; architecture Langfuse subgraph |
| **AUD-010** | Architecture | **Medium** | **PCP-10 (multi-patient schedule summary)** requires a different authorization pattern; PRD defers without design review. Premature implementation is a **cross-patient leakage** hazard. | PRD §3.5; PRD §6 out of scope discipline |
| **AUD-011** | Process | **Low** | **Deliverable naming:** **Resolved (Week1 repo):** root [`USERS.md`](USERS.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md). Historical `users.md` naming risk closed for this workspace. | PRD §7 checklist |
| **AUD-012** | Documentation / governance | **High** | **`Clinical_CoPilot_PRD.docx` (v1.0) diverges materially from `AF/PRD.md` (v1.1).** (See original audit body for bullet list.) **Governance closure (Week1):** [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md) — repo markdown authoritative; Word is reference-only. **Residual:** stakeholder Word exports still need version hygiene outside this repo. | Side-by-side: Word `Clinical_CoPilot_PRD.docx` vs `AF/PRD.md` |
| **AUD-013** | Security / RBAC | **Critical** | **`Clinical_CoPilot_TaskList_v2.docx` (v2.0) contradicts v1.1 nurse RBAC and tool model.** (Full conflict text preserved in audit v1.2 export if restored.) **Governance closure (Week1):** enforce [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md) + [`agent/access/rbac.py`](agent/access/rbac.py) / [`EVAL.md`](EVAL.md) matrix tests — **do not implement from Word** without diff. | Word v2.0 vs `AF/PRD.md` Feature 4 & 8; [`USERS.md`](USERS.md) |

---

## 5. Recommendations and remediation

| ID | Recommendation | Actionable fix (owner: team) | Verified by |
|----|----------------|------------------------------|-------------|
| **AUD-001** | Single source of truth for RBAC | [`USERS.md`](USERS.md) + [`agent/access/rbac.py`](agent/access/rbac.py); refusals named + logged. | **Done (docs + code + tests):** [`EVAL.md`](EVAL.md) matrix coverage |
| **AUD-002** | Align nurse write semantics | Agent RBAC = read-only nursing tool subset per PRD. | **Done (docs)** — option (A) in `USERS.md` |
| **AUD-003** | Fix tool count language | Reconcile external `AF/PRD.md` if needed; in-repo PRD updated. | [`PRD-AgentForge-Clinical-CoPilot-Requirements.md`](PRD-AgentForge-Clinical-CoPilot-Requirements.md) |
| **AUD-004** | Block tool split on data proof | Category filter + unit tests; operators tag imports. | [`openemr_fhir.py`](agent/tools/openemr_fhir.py); [`test_observation_category_filter.py`](agent/tests/unit/test_observation_category_filter.py) |
| **AUD-005** | Evidence performance budget | Run benchmark script; record p50/p95. | [`scripts/benchmark_fhir_latency.py`](scripts/benchmark_fhir_latency.py) — **numbers TBD** |
| **AUD-006** | Lock verification policy | ARCHITECTURE audit table + fork ADR for partial claims. | **Scaffold documented**; fork owns strip/withhold |
| **AUD-007** | Decide session keying | Stateless model documented. | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **AUD-008** | PHI guardrails | Demo posture in deploy docs; BAAs for prod. | Standing — [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **AUD-009** | Observability posture | Langfuse vs structured logs. | [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md) |
| **AUD-010** | Contain PCP-10 | Do not implement until ADR. | **Waived** per PRD |
| **AUD-011** | Submission hygiene | Root deliverable files. | **Done:** [`USERS.md`](USERS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **AUD-012** | Word PRD vs markdown | Declare authority. | [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md) |
| **AUD-013** | Word TaskList vs markdown | Do not implement from Word alone. | [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md) + RBAC tests |

---

## 6. Status / fix tracking

| Finding ID | Severity | Status | Owner | Target / note |
|--------------|----------|--------|-------|----------------|
| AUD-001 | Critical | **Resolved** (docs + code) | Agent | [`rbac.py`](agent/access/rbac.py), [`EVAL.md`](EVAL.md) |
| AUD-002 | High | **Resolved** (documentation) | Product / Docs | [`USERS.md`](USERS.md) |
| AUD-003 | Medium | **Resolved** (in-repo) / **Open** (external `AF/PRD.md`) | Docs | Ingest PRD + `USERS.md`; reconcile `AF/` if distributed |
| AUD-004 | High | **Mitigated** (agent filter + tests) | Data + Agent | Residual: fix untagged Observation data at import |
| AUD-005 | High | **Partial** | Infra | [`scripts/benchmark_fhir_latency.py`](scripts/benchmark_fhir_latency.py); append timings to appendix |
| AUD-006 | Medium | **Partial** (scaffold documented) | Product + Agent | Fork: strip/withhold ADR |
| AUD-007 | Medium | **Resolved** (scaffold — stateless) | Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| AUD-008 | Medium | **Open** / standing | Compliance | Demo posture documented; BAAs for prod PHI |
| AUD-009 | Low | **Partial** | Infra | [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md) |
| AUD-010 | Medium | **Waived** (defer) | Product | Per PRD |
| AUD-011 | Low | **Resolved** | Release | Root [`USERS.md`](USERS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| AUD-012 | High | **Governance resolved** (Week1) | Product / Docs | [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md); Word file hygiene external |
| AUD-013 | Critical | **Governance resolved** (Week1) | Product / Docs | Same; enforce in code review |

**Legend:** **Mitigated** / **Partial** = risk reduced but not fully eliminated; **Governance resolved** = authoritative docs + enforcement path exist in-repo; **Open** = still needs owner action (often external artifacts or prod gates).

---

## 7. Tools used

| Tool / artifact | Use |
|-----------------|-----|
| Repository file reads | `AF/architecture.md`, `AF/PRD.md`, `AF/Tasks.md`, `users.md` |
| Word `.docx` text extraction | Python `zipfile` + `xml.etree.ElementTree` on `word/document.xml` for `Projects/AgentForge/Clinical_CoPilot_PRD.docx` and `Clinical_CoPilot_TaskList_v2.docx` |
| Structured comparison | Manual cross-reference matrix (PRD Features ↔ Tasks PRs); Word vs markdown diff |
| **Not used** | Dynamic scanner, DAST, dependency audit, cloud CLI, OpenEMR runtime |

---

## 8. Audit history

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-28 | Engineering (AI-assisted) | Initial audit from architecture, PRD v1.1, Tasks v2.1, users.md; static scope; status table initialized |
| 1.1 | 2026-04-28 | Engineering (AI-assisted) | `users.md` rewritten to PRD Feature 8; AUD-001/AUD-002 marked resolved (documentation); executive summary updated |
| 1.2 | 2026-04-28 | Engineering (AI-assisted) | Incorporated `Clinical_CoPilot_PRD.docx` (v1.0) and `Clinical_CoPilot_TaskList_v2.docx` (v2.0); added §2.3 authority table; findings **AUD-012**, **AUD-013**; methodology + tools updated |
| 1.3 | 2026-05-03 | Engineering (AI-assisted) | §4 findings updated for Week1 code (RBAC, FHIR category filter, benchmarks); **`DOCUMENT-CONTROL.md`**; §6 status refresh; Appendix A F11 path → `agent/tests/eval/`; §2.2 scope note superseding “no rbac” |

---

## Appendix A — PRD feature ↔ architecture ↔ task trace (quick map)

| PRD feature (summary) | Architecture anchor | Tasks PR (primary) |
|----------------------|----------------------|---------------------|
| F1 OpenEMR + demo data | OpenEMR / DB subgraph | PR #01 |
| F2 Deployment + HTTPS + degrade | Nginx, compose | PR #02 |
| F3 Chat panel + session | Browser + `AgentState` | PR #08–10 |
| F4 Eight patient tools | `TOOLS_L` + FHIR/REST clients | PR #07 |
| F5 Pre-visit summary | LangGraph + tools | PR #14 |
| F6 Verification | `VERIFY_N`, grounding/domain | PR #11 |
| F7 Flagging | `POST /flag` → Langfuse | PR #09, #13 |
| F8 RBAC | `rbac.py`, retrieve enforcement | PR #12 |
| F9 Failure states | UI + agent errors | PR #09–10 |
| F10 Observability | Langfuse + PHI-safe logger | PR #13 |
| F11 Eval suite | `agent/tests/eval/` + [`EVAL.md`](EVAL.md) | PR #15 |

---

## Appendix B — Next audit revision (when code exists)

When `agent/` and OpenEMR fork land in-repo, re-run this audit with:

1. **RBAC integration tests** + manual API fuzz (role token × tool × patient).
2. **Log sampling** for raw PHI leakage (stdout, Langfuse payloads, error traces).
3. **FHIR p95 timings** on deployed URL against PRD §1.2 budgets.
4. **Verify-node** behavior on partial vs full grounding failure (eval + manual).

---

## Appendix C — Week1 repository scaffold snapshot (2026-05-01)

**Purpose:** Record **non-design** findings from the **current Git-tracked codebase** without replacing the executive summary above (which remains PRD/design-focused).

| Topic | Finding | Severity |
| --- | --- | --- |
| Runtime parity | FastAPI agent + scaffold RGV (`agent/runtime/rgv_pipeline.py`, `agent/services/chat_turn.py`) implements **ordering, bounded retry, explicit `verified`/`verification_notes`**, and **structured logs** (`agent_event`). **Record-backed attribution in assistant prose** is still **not** implemented here—fork ownership per `.planning/ROADMAP.md`. | Medium (scope transparency) |
| RBAC | Role resolution via OpenEMR `/api/user` + agent RBAC tests (`agent/access/rbac.py`, `agent/tests/`). Aligns with [`USERS.md`](USERS.md) narrative. | Low |
| Observability | Structured events exist (`agent/observability/events.py`); **token/cost** often logged as `cost_envelope=unknown` in scaffold—see [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md). | Medium |
| Evaluation | **~169** automated tests passing offline (`agent/tests`, `deploy/tests`); live OpenEMR gated by env. Snapshot: [`.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md`](.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md). | Low |
| Deployed agent | Fly app name in `fly.agent.toml` is `clinical-agent-scaffold`; public health check pattern in `README.md`. **Availability** and **spend** are operator-owned, not re-audited here. | Info |

**Summary (this appendix):** The repository **substantiates contracts and safety-oriented structure** (auth, RGV, Observation **category filter** for FHIR tools, tests, logging shape) and **does not** yet close the full **“every factual claim traceable to a record”** bar in live LLM output—that remains the **highest-risk honest gap** for the next audit revision when the fork ships.
