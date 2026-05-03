# Clinical Co-Pilot — System Audit (AUDIT.md)

**AgentForge · Gauntlet AI**  
**Audit artifact version:** 1.2 · **Date:** April 28, 2026  
**Sources reviewed:** `AF/architecture.md`, `AF/PRD.md` (v1.1), `AF/Tasks.md` (v2.1), `users.md` (RBAC — aligned with PRD Feature 8 as of v1.1), `Projects/AgentForge/Clinical_CoPilot_PRD.docx` (Word **v1.0**), `Projects/AgentForge/Clinical_CoPilot_TaskList_v2.docx` (Word **v2.0**)

---

## Executive summary (~500 words)

This audit reviews the Clinical Co-Pilot design as expressed in the Week 1 architecture narrative, **markdown** PRD **v1.1** (`AF/PRD.md`), the PR/task map **v2.1** (`AF/Tasks.md`), and `users.md` (RBAC tool matrix aligned with PRD Feature 8 as of audit v1.1). **Additionally**, two **Word** sources in `Projects/AgentForge/` were reviewed by extracting body text from the `.docx` packages: **`Clinical_CoPilot_PRD.docx` (dated Version 1.0)** and **`Clinical_CoPilot_TaskList_v2.docx` (Version 2.0)**. Those Word files are **not equivalent** to the markdown versions: they describe an **older / alternate baseline** (e.g. **10** MVP features vs **11** in v1.1, **seven** patient tools with **no vitals/labs split**, different **PCP story numbering**, generic RBAC without the **ADMIN tool matrix**, and different **LLM / HIPAA** framing). **For implementation and Gauntlet hard gates, treat `AF/PRD.md` v1.1 + `AF/Tasks.md` v2.1 as authoritative** unless product explicitly re-baselines the Word exports.

The intended system (per **v1.1 markdown + architecture**) is a FastAPI agent behind Nginx, validating OpenEMR session tokens, retrieving patient context through **eight** distinct tools (FHIR-first, REST where needed), running a LangGraph retrieve → generate → verify loop, streaming to a vanilla JS panel injected into OpenEMR, and emitting PHI-safe logs plus Langfuse traces—including explicit **`POST /flag`** audit events without re-generation.

The design is internally strong on several non-negotiable clinical-AI controls: session scoping to a single patient, programmatic verification (grounding plus domain rules), graceful degradation when the agent is down, and a stated refusal to persist conversation content to disk. The PRD’s MVP hard gates correctly force documentation, deployment, user modeling, architecture defense, and this audit before heavy implementation.

**Update (audit v1.1):** `users.md` previously contradicted PRD Feature 8 on **`ADMIN`** (full access vs restricted) and on **nurse “write notes”** vs the MVP **read-only eight-tool** matrix. **`users.md` has been rewritten** to match PRD Feature 8 (tool matrix, refusal behavior, admin security boundary). **Implementation in `agent/access/rbac.py` is still pending** (Tasks PR #12); this closes the **documentation** finding only.

A **remaining** cross-document inconsistency is in the PRD itself: the Definitions table still refers to “**7** patient context functions” while Feature 4 and the architecture diagram specify **eight** tools with labs and vitals split. That ambiguity can cause incomplete tool registration, incorrect eval coverage, or mistaken performance budgets (finding **AUD-003**, still open).

Operational and data-quality dependencies are well called out in the PRD open questions but remain **unverified in this audit**: FHIR latency against the five-second summary budget, consistent `Observation.category` tagging (`laboratory` vs `vital-signs`) in demo data, verification policy when partial claims fail grounding, and Langfuse hosting posture (self-hosted vs cloud) relative to HIPAA framing. The Tasks checklist appropriately elevates Observation category verification before the vitals/labs split lands in PR #07.

**Scope limitation (critical transparency):** This repository snapshot contains **planning and diagram documentation only**. There is **no runnable OpenEMR fork, no `agent/access/rbac.py`, and no executed benchmark or penetration test** in scope for this pass. Therefore, findings below are **design- and document-level** with **proposed verification steps**; they are not substitutes for runtime security testing, PHI log sampling, or API abuse testing against a live deployment.

Overall readiness: **RBAC narrative is unified in `users.md` with the markdown PRD v1.1**; **tool-count language in PRD §2 should still be corrected**; **Word PRD v1.0 and Word TaskList v2.0 must not be treated as equivalent to the markdown v1.1 / v2.1 pair** (see **AUD-012**, **AUD-013**); **open questions must be closed with measured evidence** before merge gates on PR #07 (EHR tools) and PR #12 (RBAC code + tests).

### Update 2026-05-03 (implementation evidence, not a re-audit)

Since audit **v1.2**, this repository gained **executable** (still demo-scoped) pieces that narrow—but do not fully close—earlier **“no code in scope”** caveats:

- **RBAC enforcement** in [`agent/access/rbac.py`](agent/access/rbac.py) with pytest coverage including [`agent/tests/eval/`](agent/tests/eval/) (**see [`EVAL.md`](EVAL.md)**).
- **OpenEMR auth** via **PHP session probe** + **Standard API Bearer** + optional **demo bypass** ([`agent/access/openemr_auth.py`](agent/access/openemr_auth.py), [`deploy/copilot_session_probe.php`](deploy/copilot_session_probe.php)).
- **Five** LLM-callable clinical tools (CSV + optional FHIR) ([`agent/tools/dispatch.py`](agent/tools/dispatch.py)).

Runtime security review, PHI log sampling, and FHIR performance **still** require a controlled environment—this note does **not** replace those activities.

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
| No deployed OpenEMR + agent stack in this workspace | Cannot validate TLS config, header behavior, real FHIR timings, or idempotency under load |
| No source code for `rbac.py`, tools, or middleware | Cannot confirm enforcement at retrieve-node vs route vs FHIR client layers |
| No live log / Langfuse sample review | Cannot confirm absence of raw PHI in stdout or third-party sinks |
| No legal / BAA interpretation | Only policy alignment to PRD §1.4 demo-data assumption is assessed |

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
| **AUD-003** | Documentation | **Medium** | **PRD still says “7 patient context functions” in Definitions while Feature 4 defines eight tools** (labs and vitals split). Causes test plan and marketing misalignment. | PRD §2 “Tool call”; PRD §4 Feature 4 |
| **AUD-004** | Data quality | **High** | **RBAC boundary for nurses depends on correct FHIR `Observation.category` tagging.** If demo or OpenEMR data mis-tags vitals/labs, vitals tool may leak lab-equivalent observations or block legitimate vitals. | PRD §3.3 NR-01 note; PRD §8 open question; Tasks PR #01 integration checklist |
| **AUD-005** | Performance | **High** | **End-to-end pre-visit summary (≤5s) is unproven** against real OpenEMR FHIR latency; PRD flags this as an open question. | PRD §1.2 metrics; PRD §8 FHIR latency question; `AF/architecture.md` parallel tool design |
| **AUD-006** | Safety / UX | **Medium** | **Verification threshold for partial unverifiable claims is undecided** (“strip + count” vs “withhold all”). Affects false confidence vs false silence tradeoff. | PRD §6 Feature 6; PRD §8 open question |
| **AUD-007** | Security | **Medium** | **Session isolation strategy** (token + patient_id vs server-side session store) is listed as open; affects concurrent session safety and replay handling. | PRD §8; architecture `AgentState` session scoping |
| **AUD-008** | Compliance | **Medium** | **Anthropic usage without BAA** is acceptable **only** under demo-data policy; any drift to real PHI invalidates the assumption. Must stay visible in architecture + runbooks. | PRD §1.4; PRD §5 stack pitfalls |
| **AUD-009** | Observability | **Low** | **Langfuse “self-hosted” vs cloud** choice affects compliance narrative; PRD asks for explicit documentation before queries. | PRD §8; architecture Langfuse subgraph |
| **AUD-010** | Architecture | **Medium** | **PCP-10 (multi-patient schedule summary)** requires a different authorization pattern; PRD defers without design review. Premature implementation is a **cross-patient leakage** hazard. | PRD §3.5; PRD §6 out of scope discipline |
| **AUD-011** | Process | **Low** | **Deliverable naming:** PRD §7 requires `USERS.md` / `ARCHITECTURE.md` at repo root; this workspace uses `users.md` and `AF/architecture.md`. Risk of submission checklist mismatch until renamed or copied. | PRD §7 checklist; Tasks file map |
| **AUD-012** | Documentation / governance | **High** | **`Clinical_CoPilot_PRD.docx` (v1.0) diverges materially from `AF/PRD.md` (v1.1).** Word PRD describes **10** MVP features (no separate “incorrect response flagging” feature as in v1.1 Feature 7; RBAC is Feature 7 in Word vs Feature 8 in markdown; **Patient Context Tools** lists **seven** retrievals **without** a dedicated **vitals** tool or `Observation` category split). **PCP user story IDs differ** (e.g. Word maps “problem list / schedule” to **PCP-08 / PCP-09** where v1.1 reserves **PCP-08** for flagging and **PCP-09** for problem list). **LLM / HIPAA** language differs (Word stack table: “treat as if BAA is in place (per Gauntlet requirement)” vs v1.1 **demo-data-only**, no BAA). | Side-by-side: Word `Clinical_CoPilot_PRD.docx` extracted body vs `AF/PRD.md` |
| **AUD-013** | Security / RBAC | **Critical** | **`Clinical_CoPilot_TaskList_v2.docx` (v2.0) contradicts v1.1 nurse RBAC and tool model.** Word task list specifies **seven** tools, **`POST /summary` calling all seven in parallel**, and RBAC examples stating **NURSE** is allowed **`labs`** while blocked from visit notes and problem list. **PRD v1.1 Feature 8** requires **eight** tools with **labs and vitals split**, and **NURSE must not** access **labs** or **visit notes** but **may** access **vitals**. Following the **Word v2.0** task list for RBAC or tool count would **violate** the v1.1 “RBAC refusal accuracy” gate and NR-03/NR-04 intent. | `Clinical_CoPilot_TaskList_v2.docx` (RBAC / seven-tool / nurse-labs passages) vs `AF/PRD.md` Feature 4 & 8; `users.md` matrix |

---

## 5. Recommendations and remediation

| ID | Recommendation | Actionable fix (owner: team) | Verified by |
|----|----------------|------------------------------|-------------|
| **AUD-001** | Single source of truth for RBAC | **Rewrite `users.md`** (and future `agent/access/rbac.py` docstring) to match PRD Feature 8 matrix: PHYSICIAN = 8 tools; NURSE = subset; ADMIN = demographics + schedule only; refusals must **name role + tool** and log. Remove “admin highest” unless explicitly scoped to **OpenEMR core** (out of agent scope). | **Done (docs):** `users.md` 2026-04-28. **Pending:** `agent/access/rbac.py` + PR #12 `test_rbac.py`; demo video RBAC refusal |
| **AUD-002** | Align nurse write semantics | Either **(A)** remove nurse “write notes” from agent RBAC doc and scope to OpenEMR-native documentation only, or **(B)** add a PRD amendment + tool design if nursing notes via agent are in scope (currently not in Feature list). | **Done (docs):** option **(A)** in `users.md` 2026-04-28. **Pending:** PRD traceability if product later chooses **(B)** |
| **AUD-003** | Fix tool count language | Update PRD §2 definition of “Tool call” to **eight** tools; grep PRD for “seven/7” in tool context. | Editorial PR on `AF/PRD.md` |
| **AUD-004** | Block tool split on data proof | Complete Tasks PR #01 checklist item: **`test_fhir_observation_category_tags_present`**; document fallback strategy if tags missing. | Integration test pass; ADR 005 reference |
| **AUD-005** | Evidence performance budget | Run scripted FHIR benchmarks (Patient + 8 resource patterns) on local + deployed URL; record p50/p95 in AUDIT appendix next revision. | PR #03 follow-up or PR #07 gate |
| **AUD-006** | Lock verification policy | Decide threshold before verify node implementation; add to `ARCHITECTURE.md` + ADR; add eval cases for partial failure. | PR #11 tests + eval baseline |
| **AUD-007** | Decide session keying | Document chosen model in `ARCHITECTURE.md`; if needed, add server session store + TTL aligned to PRD 30 min inactivity. | PR #08–09 design review |
| **AUD-008** | PHI guardrails | Add prominent **“demo data only”** banner in deployment docs; block production keys in `.env.example`; CI check for secrets. | PR #01–02 |
| **AUD-009** | Observability posture | Confirm Langfuse deployment mode; if cloud, document data handling per PRD. | `docs/observability.md` (Tasks PR #13) |
| **AUD-010** | Contain PCP-10 | Do not implement schedule-wide summary until multi-patient auth ADR exists and is reviewed. | PRD §3.5 gate |
| **AUD-011** | Submission hygiene | Add root-level `USERS.md` / `ARCHITECTURE.md` that satisfy PRD naming **or** adjust submission package with explicit mapping note. | PRD §7 checklist |
| **AUD-012** | Word PRD v1.0 vs markdown v1.1 | **Declare authority:** Add a one-page “document control” note at top of Word export or stop distributing Word as parallel spec. **Export Word v1.1** from markdown (or vice versa) so filenames/versions match content. Reconcile **PCP IDs** and **feature numbering** in any stakeholder deck. | Single canonical PRD; version table in README |
| **AUD-013** | Word TaskList v2.0 vs markdown v2.1 | **Do not implement RBAC or tool lists from `Clinical_CoPilot_TaskList_v2.docx` without diffing to `AF/Tasks.md` v2.1.** Update Word export to **v2.1** (eight tools, `vitals.py`, `POST /flag`, nurse matrix = demographics, medications, **vitals**, allergies, schedule; ADMIN restricted). Add CI or checklist item: “RBAC unit tests assert v1.1 matrix.” | PR #07 + #12 tests; `test_rbac.py` parameterized from `users.md` / PRD |

---

## 6. Status / fix tracking

| Finding ID | Severity | Status | Owner | Target / note |
|--------------|----------|--------|-------|----------------|
| AUD-001 | Critical | **Resolved** (documentation) | Docs + Agent | `users.md` aligned 2026-04-28; code in PR #12 still required |
| AUD-002 | High | **Resolved** (documentation) | Product / Docs | Nurse = read-only tool subset per PRD; `users.md` updated 2026-04-28 |
| AUD-003 | Medium | **Open** | Docs | Single PRD edit |
| AUD-004 | High | **Open** | Data + PR #01 | Gate PR #07 |
| AUD-005 | High | **Open** | Infra + Agent | Measure after OpenEMR runs |
| AUD-006 | Medium | **Open** | Product + Agent | Pre PR #11 |
| AUD-007 | Medium | **Open** | Architecture | Pre PR #08–09 |
| AUD-008 | Medium | **Open** | Compliance narrative | Standing until real PHI |
| AUD-009 | Low | **Open** | Infra | PR #13 |
| AUD-010 | Medium | **Waived** (defer) | Product | Intentionally not built Week 1 per PRD |
| AUD-011 | Low | **Open** | Release | Before submission |
| AUD-012 | High | **Open** | Product / Docs | Reconcile or retire Word PRD v1.0 as parallel spec |
| AUD-013 | Critical | **Open** | Product / Docs | Update Word TaskList to v2.1 parity or mark “superseded” |

**Legend:** Open = not remediated; **Resolved (documentation)** = spec/truth captured in repo docs; implementation may still be **Open** in code; Waived = accepted deferral per PRD.

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
| F11 Eval suite | `agent/eval/` | PR #15 |

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

**Summary (this appendix):** The repository **substantiates contracts and safety-oriented structure** (auth, RGV, tests, logging shape) and **does not** yet close the full **“every factual claim traceable to a record”** bar in live LLM output—that remains the **highest-risk honest gap** for the next audit revision when the fork ships.
