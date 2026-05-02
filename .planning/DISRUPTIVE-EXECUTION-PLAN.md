# Disruptive execution plan — LLM tools, evals, live stability

**Audience:** Owner + agents coordinating “final” Gauntlet-style delivery.  
**Reality check:** The request spans **product**, **data engineering**, **ML orchestration**, **SRE**, and **clinical safety** — typically **multiple engineer-weeks** even with a mature OpenEMR fork. This file sequences work and gives **ETAs** so progress is measurable.

---

## ETA summary (calendar time)

| Track | Scope | Who / what | Rough ETA |
| --- | --- | --- | --- |
| **A. LLM-native tools (≥5) + model-chosen calls** | OpenAI `tools` loop, RBAC on each execution, structured outputs, wire into `/agent/chat` | 1 senior backend + review | **5–10 days** |
| **B. Behavioral evals (≥30)** | Mocked tool-calling sequences, RBAC denials, bad args, empty cohort, contract tests; optional tiny live subset | Same + QA mindset | **4–8 days** (parallel with A after interfaces freeze) |
| **C. Realistic seed + “no setup” demo** | Either **(i)** Synthea→OpenEMR import pipeline **or** **(ii)** docker-compose with OpenEMR + MariaDB + agent + **documented one-command** bootstrap | DevOps + EMR familiarity | **1–3 weeks** (import is the long pole) |
| **D. 5–7 clinician workflows E2E** | UX copy, chat-ui flows, golden prompts, acceptance criteria per [`USERS.md`](../USERS.md) UC-* | Product + eng | **1–2 weeks** (after A + partial C) |
| **E. Live stability** | Fly health, autoscale, secrets, rate limits, rollback, monitoring | SRE | **ongoing**; first hardening pass **3–7 days** |

**Combined (single serial team):** expect **~4–8 weeks** to a defensible “final” with real EMR-backed tools and seeded cohort. **Parallelizing** (deploy + agent + eval in parallel) can compress toward **~3–5 weeks** wall-clock if decisions unblock quickly.

**What one coding session can deliver:** a **vertical slice** (CSV-backed tools + tool loop behind a flag + first eval pack). Full OpenEMR seeding and 30+ deep behavioral tests exceed a single session.

---

## Guiding constraints

- **Do not** rely on `--dangerously-skip-permissions` for clinical or PHI workflows; keep least-privilege defaults.
- **RBAC** remains authoritative per [`USERS.md`](../USERS.md) Part 2 — every tool execution calls `assert_tool_allowed`.
- **Chart scope:** tool args must not fetch a different `patient_id` than the session’s `ClinicalTurnState.patient_id`.

---

## Phase checklist (dependency order)

1. **Tool contracts** — JSON schemas + canonical mapping to `demographics` | `medications` | `labs` | `vitals` | `allergies` (first five shipped in-repo slice).
2. **Data backend** — start with **fixture CSVs** (`fixtures/sample-patients/`) for deterministic evals; **promote** to OpenEMR FHIR in fork (`DISRUPTIVE` track C).
3. **OpenAI tool loop** — `chat.completions` with `tools`, handle `tool_calls`, append tool results, cap iterations.
4. **Chat integration** — feature flag (e.g. `AGENT_LLM_CSV_TOOLS=1`) + merge tool traces into `tool_results` for verify/logging.
5. **Evals** — `agent/tests/eval/` + marker `llm_eval` / `csv_tools`; default CI stays fast (`-m "not llm_eval"` optional).
6. **Seeding / compose** — fix `docker-compose` story, add import automation or documented bulk FHIR path.
7. **Workflow scripts** — 5–7 scripted clinician prompts + expected JSON keys for demo and regression.

---

## Revision

| Date | Note |
| --- | --- |
| 2026-05-02 | Initial plan + ETA bands. |
