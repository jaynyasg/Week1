# Project showcase — Clinical Co-Pilot (Week1)

**Purpose:** A single, readable narrative of **what this repository delivers**, **why key choices were made**, and **where to find proof** (tests, docs, deploy). Intended for reviewers, demos, and future-you after scope changes.

**Living document:** Update this file when milestones close, tests counts shift materially, or deployment URLs/cost figures change. Append a row to **§ Revision history** at the bottom each time.

**Last updated:** 2026-05-02

---

## 1. Executive overview

This project is a **role-safe clinical copilot** integrated with **OpenEMR**, deployed as a **separate FastAPI agent** on **Fly.io**, with a **retrieve → generate → verify (RGV)** runtime shape, **structured observability hooks**, and an **automated test suite** that proves HTTP contracts, auth boundaries, and scaffold behavior **without** claiming full production LLM + FHIR + record-backed attribution in prose (those remain **fork / deployed-stack** work—see [`.planning/ROADMAP.md`](.planning/ROADMAP.md)).

The **design intent** (users, use cases, verification philosophy, observability minimums) is documented in canonical markdown; the **code** proves contracts and safety-oriented structure so the OpenEMR fork can inherit a verifiable foundation.

---

## 2. Architecture — decisions and evidence

| Decision | What we chose | Why it matters | Where it lives |
| --- | --- | --- | --- |
| **Agent placement** | **Separate Fly app** from OpenEMR (`fly.agent.toml`, `Dockerfile.agent`) | Independent deploy, scale, and failure domain from PHP stack | [`fly.agent.toml`](fly.agent.toml), [`deploy/README-fly-agent.md`](deploy/README-fly-agent.md) |
| **Auth boundary** | Validate **OpenEMR session** via **`/api/user`** (Bearer and/or Cookie); no second login | Trust inherits from EHR; role comes from same source clinicians already use | [`agent/access/openemr_auth.py`](agent/access/openemr_auth.py), [`agent/http/deps.py`](agent/http/deps.py) |
| **RGV loop** | **Retrieve → generate → verify** with **bounded retry** (`MAX_VERIFY_RETRIES`) | Ordering and graceful **`verified: false`** exit are explicit—not silent success | [`agent/runtime/rgv_pipeline.py`](agent/runtime/rgv_pipeline.py) |
| **HTTP API** | `POST /agent/chat` with multi-turn **`messages`**, **`ChatResponse`** schema (`verified`, `verification_notes`, `tool_result_keys`, …) | Stable JSON contract for UI and eval | [`agent/http/schemas.py`](agent/http/schemas.py), [`agent/http/routes_chat.py`](agent/http/routes_chat.py) |
| **Scaffold vs fork** | In-repo **scaffold** retrieve/generate/verify; **full PRD runtime** on fork | Honest scope: contracts + tests here; EMR-deep integration there | [`.planning/ROADMAP.md`](.planning/ROADMAP.md) Phase 3 notes, [`ARCHITECTURE.md`](ARCHITECTURE.md) executive summary |

**Deeper narrative:** [`ARCHITECTURE.md`](ARCHITECTURE.md) (includes ~500-word executive summary + mermaid target diagram).

---

## 3. Users and use cases

**Source of truth:** [`USERS.md`](USERS.md) **Part 1** — Stage 4 hard gate.

| Theme | Summary |
| --- | --- |
| **Primary user** | Ambulatory PCP (**Dr. Sam Rivera** archetype), **~20-patient** clinic day, chart-grounded answers—not generic LLM advice |
| **Workflow grounding** | Morning schedule scan → **moments between rooms** → in-visit → documentation; copilot enters **after** the clinician is already in chart context |
| **Use cases UC-01 … UC-06** | Each includes **why not a dashboard / sorted list / template** and **why a conversational agent** is the right shape |
| **RBAC** | **Part 2** of [`USERS.md`](USERS.md): eight tools, PHYSICIAN / NURSE / ADMIN matrix, explicit refusal semantics |

**Alias file:** [`USER.md`](USER.md) points to `USERS.md` for checklist compatibility.

---

## 4. Evaluation

| Aspect | Status / intent |
| --- | --- |
| **Automated suite** | **`pytest`** over `agent/tests` and `deploy/tests`; typical offline run **~162 passed**, **~15 skipped** (live OpenEMR, optional gates)—**re-run to refresh** |
| **What it proves** | RGV ordering, multi-turn history, auth/RBAC, OpenAPI contract, OpenEMR fetch edge cases (mocked), HTTP observability fields, deploy manifest checks, chat JSON shape vs `ChatResponse` |
| **Live / gated** | Optional `RUN_LIVE_OPENEMR_E2E` tests and latency gates documented in [`.env.example`](.env.example) |
| **Traceability** | [`.planning/REQ-TEST-TRACEABILITY.md`](.planning/REQ-TEST-TRACEABILITY.md) |

**Commands & snapshot pointer:** [`.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md`](.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md), [`README.md`](README.md) (Agent tests section).

---

## 5. AI cost analysis

| Aspect | Status |
| --- | --- |
| **Deliverable** | [`AI-COST-ANALYSIS.md`](AI-COST-ANALYSIS.md) — dev spend table (**TBD**), tiered **100 → 100K** user framing, architectural implications per tier |
| **Runtime honesty** | Scaffold logs often use **`cost_envelope="unknown"`** until provider usage is wired—see [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md) |

**Update before submission:** Replace **TBD** with real API and infra numbers.

---

## 6. Observability

| Minimum question (rubric) | Repo stance |
| --- | --- |
| What ran, in what order? | RGV ordering enforced; **`chat_turn_complete`** (and related) **`agent_event`** logs |
| Step timings? | **`rgv_duration_ms`** on structured logs; per-phase breakdown still **partial** |
| Tool failures? | RBAC refusals and OpenEMR auth errors structured; full FHIR tool failures **fork-side** |
| Tokens / cost? | **Gap** until wired—documented in observability gap file |

**Inventory:** [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md) · **Implementation stubs:** [`agent/observability/`](agent/observability/).

---

## 7. Repository and delivery hygiene (high level)

Non-exhaustive list of engineering work that supports the narrative above:

- **CI:** Ruff + pytest on GitHub Actions and GitLab; **path-gated** chat-ui build and npm audit where configured  
- **Dependabot:** Weekly pip (root + deploy) and npm (`chat-ui`)  
- **Operator docs:** [`deploy/docs/operator-runbook.md`](deploy/docs/operator-runbook.md), [`deploy/README-fly-agent.md`](deploy/README-fly-agent.md)  
- **Onboarding:** `make doctor` / `scripts/doctor.ps1` · **Troubleshooting** table in [`README.md`](README.md)  

*(Exact git history: use `git log`; this section stays summary-level.)*

---

## 8. Audit and risk posture

Design-time audit and Word-vs-markdown caveats: [`AUDIT.md`](AUDIT.md).  
Scaffold snapshot appendix ties repo reality to audit expectations without overstating runtime parity.

---

## 9. How to refresh this document

1. Run `python -m pytest agent/tests deploy/tests -q` and note **passed / skipped**.  
2. Re-read [`.planning/STATE.md`](.planning/STATE.md) and [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for phase completion.  
3. Update **§4 Evaluation** counts and **§5** if cost tables are filled.  
4. If **users/use cases** change, edit [`USERS.md`](USERS.md) Part 1 first, then summarize here.  
5. Append **§ Revision history** with date and one-line summary.

---

## Revision history

| Date | Changes |
| --- | --- |
| 2026-05-02 | Initial `PROJECT-SHOWCASE.md`: architecture, users, eval, cost, observability, hygiene pointers; living-doc process. |
