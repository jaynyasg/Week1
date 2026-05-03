# Project showcase — Clinical Co-Pilot (Week1)

**Purpose:** A single, readable narrative of **what this repository delivers**, **why key choices were made**, and **where to find proof** (tests, docs, deploy). Intended for reviewers, demos, and future-you after scope changes.

**Living document:** Update this file when milestones close, tests counts shift materially, deployment URLs/cost figures change, the **stack** (§2) shifts, or **interview answers** (§10) need to reflect new audit/architecture/eval evidence. Append a row to **§ Revision history** at the bottom each time.

**Last updated:** 2026-05-03

---

## 1. Executive overview

This project is a **role-safe clinical copilot** integrated with **OpenEMR**, deployed as a **separate FastAPI agent** on **Fly.io**, with a **retrieve → generate → verify (RGV)** runtime shape, **structured observability hooks**, and an **automated test suite** that proves HTTP contracts, auth boundaries, and scaffold behavior **without** claiming full production LLM + FHIR + record-backed attribution in prose (those remain **fork / deployed-stack** work—see [`.planning/ROADMAP.md`](.planning/ROADMAP.md)).

### 1.1 Synthea cohort + live OpenEMR path

- **Offline / demo cohort:** [`fixtures/sample-patients/`](fixtures/sample-patients/README.md) holds **Synthea-shaped CSV** exports (patients, encounters, observations, medications, allergies, …). The agent loads them when **OpenEMR FHIR** credentials are not configured (`source: csv` in tool payloads).
- **Import to OpenEMR:** [`scripts/import_synthea_to_openemr.py`](scripts/import_synthea_to_openemr.py) loads the same cohort into MariaDB for a Fly-hosted OpenEMR; [`scripts/verify_import.py`](scripts/verify_import.py) smoke-checks imported rows.
- **Seed patient (demo / evals):** UUID **`f1aa52b9-aded-3188-9386-012244805ebf`** (Maurice742 Brekke496) appears across workflows, fixtures, and behavioral tests.
- **FHIR-backed tools:** With `OPENEMR_BASE_URL` + `OPENEMR_FHIR_CLIENT_ID` + `OPENEMR_FHIR_CLIENT_SECRET`, the five clinical tools prefer **`openemr_fhir`** and fall back to CSV automatically when FHIR is unavailable.

### 1.2 Clinician workflows + LLM-callable tools

- **Seven scripted demo prompts** (roles, RBAC edges, expected tool patterns): [`deploy/CLINICIAN-WORKFLOWS.md`](deploy/CLINICIAN-WORKFLOWS.md).
- **Five OpenAI function tools** the model may invoke (each scoped to `patient_id` and RBAC-mapped to PRD logical tools): **`get_patient_demographics`**, **`list_active_medications`**, **`list_recent_laboratory_results`**, **`list_recent_vital_signs`**, **`list_allergies`** — see [`agent/tools/dispatch.py`](agent/tools/dispatch.py). [`USERS.md`](USERS.md) Part 2 still defines **eight** logical tools for PRD alignment; `problem_list`, `visit_notes`, and `schedule` are **not** yet exposed as model functions in this scaffold.
- **Structured chat response:** Successful turns can include **`tool_execution_summary`** (per-function status, headline counts, RBAC refusals) for demo and ops review.

### 1.3 Three ways to authenticate `POST /agent/chat`

| Mode | When to use | How it works (summary) |
| --- | --- | --- |
| **OpenEMR UI session (Cookie)** | Embedded chat in OpenEMR (same origin) or any client that can forward browser cookies | `Cookie` header (and optionally `X-OpenEMR-Browser-Cookies` for `document.cookie` mirroring). Agent validates with **`GET {OPENEMR_BASE_URL}/interface/copilot_session_probe.php`** (PHP reads `OpenEMR` session; returns JSON groups for role mapping). |
| **Bearer (Standard API)** | API clients, curl, automation with an OAuth2 access token | `Authorization: Bearer …`. Agent validates with **`GET {OPENEMR_BASE_URL}/apis/{OPENEMR_SITE_ID}/api/user`** (not the old single `/api/user` path). |
| **Demo bypass** | Non-PHI demos only (`AGENT_DEMO_BYPASS=1`) | Header **`X-Agent-Demo-Role: PHYSICIAN|NURSE|ADMIN`** skips OpenEMR validation; **never** enable with real PHI. |

**Why keep all three:** Embedded clinicians already have a **session**—no separate “copilot login.” **Bearer** supports **machine and integration** callers that never hold PHP cookies. **Demo bypass** supports **offline/Gauntlet demos** without standing up a full OpenEMR session, isolated by env + header.

The **design intent** (users, use cases, verification philosophy, observability minimums) is documented in canonical markdown; the **code** proves contracts and safety-oriented structure so the OpenEMR fork can inherit a verifiable foundation.

---

## 2. Tools, software, and platforms

Everything below is **in-repo or CI-visible** unless marked *intent* (planned on fork / production path). **Why chosen** is engineering rationale for *this* project, not a generic vendor pitch.

### 2.1 Language, runtime, and packaging

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| **Python 3.12** | Agent implementation language; CI pins this version | Strong typing ecosystem, async I/O, team velocity; matches GitHub Actions / GitLab CI images |
| **`requirements.txt`** | Dev + test dependencies (root) | Single install for contributors and CI before `pytest` / `ruff` |
| **`deploy/requirements-agent.txt`** | Slimmer **production** agent image deps (+ **uvicorn**) | Smaller Fly image surface; excludes test-only packages |

### 2.2 Agent service (backend)

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| [**FastAPI**](https://fastapi.tiangolo.com/) | HTTP API (`/agent/chat`, `/agent/health`, …), dependency injection for auth and rate limits | OpenAPI-first, async-friendly, Pydantic-native request/response validation—fits contract-heavy clinical API |
| [**Uvicorn**](https://www.uvicorn.org/) | ASGI server in the Fly container | Standard, lightweight ASGI host for FastAPI; `uvicorn[standard]` for production extras |
| [**Pydantic**](https://docs.pydantic.dev/) (via FastAPI) | `ChatRequest` / `ChatResponse` schemas, validation errors → **422** | Typed JSON contracts and clear failure modes for UI + eval |
| [**httpx**](https://www.python-httpx.org/) | Async HTTP to OpenEMR **session probe** (cookies) or **Standard API** `/apis/{site}/api/user` (Bearer), optional live smoke tests | Modern async client; `MockTransport` supports unit tests without the network |
| [**OpenAI Python SDK**](https://github.com/openai/openai-python) | Optional **LLM-backed** `scaffold_generate` when `OPENAI_API_KEY` is set | Vendor-neutral “real model” path without locking the scaffold to one host pattern; degrades to echo when unset |
| [**SlowAPI**](https://github.com/laurentS/slowapi) | Optional rate limiting on chat route when env-configured | Rate limits are a clinical-safety / abuse-control primitive for a public HTTP agent |
| [**python-dotenv**](https://github.com/theskumar/python-dotenv) | Load local `.env` for dev (gitignored) | Keeps secrets out of code while matching Fly secret names conceptually |

### 2.3 Chat UI (frontend)

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| [**React**](https://react.dev/) 18 | Chat panel UI | Small surface area, embeddable in OpenEMR or standalone; wide hiring/tooling familiarity |
| [**TypeScript**](https://www.typescriptlang.org/) | Typed client code | Safer refactors against evolving agent JSON contracts |
| [**Vite**](https://vitejs.dev/) 5 | Dev server, production build, `VITE_*` env injection | Fast local feedback; build args support Fly embed (`VITE_AGENT_BASE_URL`, `VITE_EMBEDDED`, base path) |
| **npm** | Install and CI for `chat-ui/` | Ecosystem default for Vite/React; lockfile for reproducible builds |

### 2.4 Quality, tests, and local workflow

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| [**pytest**](https://pytest.org/) | Unit + integration tests under `agent/tests`, `deploy/tests` | De facto Python standard; fixtures + parametrize fit HTTP and auth matrices |
| [**pytest-asyncio**](https://pytest-asyncio.readthedocs.io/) | Async tests (`fetch_openemr_user_json`, etc.) | Matches async FastAPI / httpx call paths |
| [**Ruff**](https://docs.astral.sh/ruff/) | Lint + format check on `agent/` (CI + optional pre-commit) | Single fast tool replacing flake8/isort stacks; matches CI |
| [**pre-commit**](https://pre-commit.com/) *(optional)* | Local hooks running Ruff on `agent/` | Catches style/issues before push; documented in [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| **GNU Make** *(optional)* | `Makefile` targets (`pytest`, `doctor`, `chat-ui-build`, …) | Cross-platform enough for devs with Git Bash; shortcuts reduce onboarding friction |

### 2.5 Integration target and data model (*intent / fork*)

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| [**OpenEMR**](https://www.open-emr.org/) | Real-world EHR: session validation, future FHIR/REST tool sources | Assignment and architecture target; **this repo** validates sessions and documents RBAC against OpenEMR roles |
| **FHIR R4** *(architecture / fork)* | Primary chart read model in [`ARCHITECTURE.md`](ARCHITECTURE.md) | Standardized patient data access; Observation category split supports labs vs vitals RBAC |

### 2.6 Deployment and operations

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| [**Fly.io**](https://fly.io/) | Hosts **agent** app (`fly.agent.toml`) separately from OpenEMR stack | Simple container deploy, health checks, secrets, regional VMs; matches “two app” topology in roadmap |
| [**Docker**](https://www.docker.com/) | `Dockerfile.agent` builds the agent image | Reproducible runtime parity dev→CI→Fly |
| **Shell / PowerShell scripts** | Smoke tests, `doctor` onboarding | Lowest friction for operators without installing extra CLIs |

### 2.7 CI/CD and dependency hygiene

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| [**GitHub Actions**](https://github.com/features/actions) | Ruff, pytest, optional path-gated chat-ui jobs (`.github/workflows/`) | Native to GitHub; `dorny/paths-filter` avoids burning minutes when `chat-ui/` unchanged |
| **GitLab CI** | Parallel pipeline (`.gitlab-ci.yml`) | Matches Gauntlet / org hosting on GitLab |
| [**Dependabot**](https://docs.github.com/en/code-security/dependabot) | Weekly PRs for pip (root + `deploy/`) and npm (`chat-ui/`) | Keeps supply chain patches flowing without manual polling |

### 2.8 Documentation and planning

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| **Markdown** | `README`, `USERS`, `ARCHITECTURE`, `AUDIT`, `.planning/*` | Diff-friendly, reviewable, **authoritative** over Word per project policy |
| [**Mermaid**](https://mermaid.js.org/) | Diagrams inside `ARCHITECTURE.md` | Renders in GitHub/GitLab; stays next to prose |

### 2.9 Version control

| Item | What it does here | Why it was chosen |
| --- | --- | --- |
| **Git** | Source history | Industry baseline; supports fork workflow toward OpenEMR integration |

---

## 3. Architecture — decisions and evidence

| Decision | What we chose | Why it matters | Where it lives |
| --- | --- | --- | --- |
| **Agent placement** | **Separate Fly app** from OpenEMR (`fly.agent.toml`, `Dockerfile.agent`) | Independent deploy, scale, and failure domain from PHP stack | [`fly.agent.toml`](fly.agent.toml), [`deploy/README-fly-agent.md`](deploy/README-fly-agent.md) |
| **Auth boundary** | **Cookie/UI:** PHP session probe [`deploy/copilot_session_probe.php`](deploy/copilot_session_probe.php) → JSON groups. **Bearer:** `GET /apis/{site}/api/user`. **Optional demo:** `AGENT_DEMO_BYPASS` + `X-Agent-Demo-Role`. No second login for real sessions. | Trust inherits from EHR; role comes from OpenEMR-backed validation or narrow demo header | [`agent/access/openemr_auth.py`](agent/access/openemr_auth.py), [`agent/http/deps.py`](agent/http/deps.py), [§1.3 above](#13-three-ways-to-authenticate-post-agentchat) |
| **RGV loop** | **Retrieve → generate → verify** with **bounded retry** (`MAX_VERIFY_RETRIES`) | Ordering and graceful **`verified: false`** exit are explicit—not silent success | [`agent/runtime/rgv_pipeline.py`](agent/runtime/rgv_pipeline.py) |
| **HTTP API** | `POST /agent/chat` with multi-turn **`messages`**, **`ChatResponse`** schema (`verified`, `verification_notes`, `tool_result_keys`, …) | Stable JSON contract for UI and eval | [`agent/http/schemas.py`](agent/http/schemas.py), [`agent/http/routes_chat.py`](agent/http/routes_chat.py) |
| **Scaffold vs fork** | In-repo **scaffold** retrieve/generate/verify; **full PRD runtime** on fork | Honest scope: contracts + tests here; EMR-deep integration there | [`.planning/ROADMAP.md`](.planning/ROADMAP.md) Phase 3 notes, [`ARCHITECTURE.md`](ARCHITECTURE.md) executive summary |

**Deeper narrative:** [`ARCHITECTURE.md`](ARCHITECTURE.md) (includes ~500-word executive summary + mermaid target diagram).

---

## 4. Users and use cases

**Source of truth:** [`USERS.md`](USERS.md) **Part 1** — Stage 4 hard gate.

| Theme | Summary |
| --- | --- |
| **Primary user** | Ambulatory PCP (**Dr. Sam Rivera** archetype), **~20-patient** clinic day, chart-grounded answers—not generic LLM advice |
| **Workflow grounding** | Morning schedule scan → **moments between rooms** → in-visit → documentation; copilot enters **after** the clinician is already in chart context |
| **Use cases UC-01 … UC-06** | Each includes **why not a dashboard / sorted list / template** and **why a conversational agent** is the right shape |
| **RBAC** | **Part 2** of [`USERS.md`](USERS.md): eight tools, PHYSICIAN / NURSE / ADMIN matrix, explicit refusal semantics |

**Alias file:** [`USER.md`](USER.md) points to `USERS.md` for checklist compatibility.

---

## 5. Evaluation

| Aspect | Status / intent |
| --- | --- |
| **Behavioral eval pack** | **[`EVAL.md`](EVAL.md)** — **53** core tests (RBAC matrix, mocked OpenAI tool loop, CSV/Synthea fixture smoke) + **21** edge-case / failure-mode tests under `agent/tests/eval/` (**74** total); no live LLM required |
| **Full automated suite** | **`pytest`** over `agent/tests` and `deploy/tests`; counts drift with new tests—**re-run to refresh** |
| **What it proves** | RGV ordering, multi-turn history, auth/RBAC, OpenAPI contract, OpenEMR HTTP edge cases (mocked), tool dispatch + scope violations, HTTP observability fields, deploy manifest checks, chat JSON shape vs `ChatResponse` |
| **Live / gated** | Optional `RUN_LIVE_OPENEMR_E2E` tests and latency gates documented in [`.env.example`](.env.example) |
| **Traceability** | [`.planning/REQ-TEST-TRACEABILITY.md`](.planning/REQ-TEST-TRACEABILITY.md) |

**Commands & snapshot pointer:** [`.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md`](.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md), [`README.md`](README.md) (Agent tests section).

---

## 6. AI cost analysis

| Aspect | Status |
| --- | --- |
| **Deliverable** | [`AI-COST-ANALYSIS.md`](AI-COST-ANALYSIS.md) — dev spend table (**TBD**), tiered **100 → 100K** user framing, architectural implications per tier |
| **Runtime honesty** | Scaffold logs often use **`cost_envelope="unknown"`** until provider usage is wired—see [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md) |

**Update before submission:** Replace **TBD** with real API and infra numbers.

---

## 7. Observability

| Minimum question (rubric) | Repo stance |
| --- | --- |
| What ran, in what order? | RGV ordering enforced; **`chat_turn_complete`** (and related) **`agent_event`** logs |
| Step timings? | **`rgv_duration_ms`** on structured logs; per-phase breakdown still **partial** |
| Tool failures? | RBAC refusals and OpenEMR auth errors structured; full FHIR tool failures **fork-side** |
| Tokens / cost? | **Gap** until wired—documented in observability gap file |

**Inventory:** [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md) · **Implementation stubs:** [`agent/observability/`](agent/observability/).

---

## 8. Repository and delivery hygiene (high level)

Non-exhaustive list of engineering work that supports the narrative above:

- **CI:** Ruff + pytest on GitHub Actions and GitLab; **path-gated** chat-ui build and npm audit where configured  
- **Dependabot:** Weekly pip (root + deploy) and npm (`chat-ui`)  
- **Operator docs:** [`deploy/docs/operator-runbook.md`](deploy/docs/operator-runbook.md), [`deploy/README-fly-agent.md`](deploy/README-fly-agent.md)  
- **Onboarding:** `make doctor` / `scripts/doctor.ps1` · **Troubleshooting** table in [`README.md`](README.md)  
- **Synthetic patient CSVs:** [`fixtures/sample-patients/README.md`](fixtures/sample-patients/README.md) + `scripts/validate_sample_patient_fixtures.py` (optional full FK validation; `--quick` in unit tests; **GitHub** `workflow_dispatch` [`.github/workflows/validate-sample-fixtures.yml`](.github/workflows/validate-sample-fixtures.yml); **GitLab** manual job `validate-sample-fixtures`)

*(Exact git history: use `git log`; this section stays summary-level.)*

---

## 9. Audit and risk posture

Design-time audit and Word-vs-markdown caveats: [`AUDIT.md`](AUDIT.md).  
Scaffold snapshot appendix ties repo reality to audit expectations without overstating runtime parity.

---

## 10. Interview-style Q&A (review prep)

Short answers you can expand verbally in a live interview. **Evidence** links point to canonical docs or code; refresh when the fork or production stack closes new gaps.

### Your Audit

**Walk us through your most important finding.**  
The audit’s highest-leverage finding is **source-of-truth drift**: exported **Word** PRD / task list **v1.0 / v2.0** is **not** the same baseline as **markdown PRD v1.1 + Tasks v2.1**—different feature counts, **no labs/vitals split**, weaker **ADMIN** RBAC story, and different LLM/HIPAA framing (see [`AUDIT.md`](AUDIT.md) executive summary and **AUD-012 / AUD-013**). Building from Word alone would bake the wrong tool surface and the wrong security posture. A close second is **AUD-003**: PRD wording still says “**seven**” patient-context functions while Feature 4 and architecture require **eight** tools—easy to ship an incomplete RBAC/register matrix if nobody reconciles the text.

**What would you have missed if you had skipped the audit and gone straight to building?**  
You would likely have (1) **under-built RBAC** (especially **ADMIN** and nurse boundaries), (2) **merged labs and vitals** in one tool and lost a permission boundary the PRD treats as safety-relevant, (3) **skipped explicit verification / degradation contracts** because “we’ll add safety later,” and (4) **underestimated operational unknowns** (FHIR latency, `Observation.category` consistency, Langfuse hosting vs HIPAA narrative) that the audit elevates before EHR tool PRs land.

**How did the audit change your AI integration plan?**  
It **forced markdown authority** over Word exports, aligned **`USERS.md`** / RBAC narrative to **PRD Feature 8**, and made **fork vs in-repo scaffold** scope explicit in [`.planning/AI-ARCHITECTURE.md`](.planning/AI-ARCHITECTURE.md) and [`.planning/ROADMAP.md`](.planning/ROADMAP.md) so the AI layer is not oversold as “fully executable” before OpenEMR integration work exists. Practically: **contracts and tests first**, then fork work carries **record-backed verification** and real tool failure modes.

---

### Your Architecture

**Why did you design the verification layer the way you did?**  
Verification is **programmatic first** (deterministic, testable) inside a **retrieve → generate → verify** loop with **bounded retry** (`MAX_VERIFY_RETRIES` in [`agent/runtime/rgv_pipeline.py`](agent/runtime/rgv_pipeline.py)): one failed verify pass can trigger a **single** re-generation, then the pipeline **stops** and returns text with **`verified: false`** rather than looping or silently succeeding. That matches the clinical bar “**don’t pretend you proved it**.” The scaffold verifier is intentionally simple (presence of tool bundle, synthetic retry path); the **fork** owns richer **grounding + domain rules** while this repo locks the **HTTP contract** (`verified`, `verification_notes`, `verify_retry_count` on [`ChatResponse`](agent/http/schemas.py)).

**What does your agent do when a tool fails or a record is missing?**  
Today’s behavior is **layered**:
- **RBAC / policy “tool not allowed”** → refusal with explicit role + tool naming and structured logs (see [`USERS.md`](USERS.md) Part 2 and tests around tool refusal logging).
- **OpenEMR session / HTTP failure** on session probe or Standard API **`/api/user`** → **`OpenEMRAuthError`** mapped to **401** with structured `detail` (no silent downgrade to “guest”).
- **Scaffold verify** with missing retrieve payload → verify fails; bounded retry may recover; else **`verified: false`** with notes so the UI and operator logs show **unverified** output.
- **Real FHIR tool failures** (timeouts, partial pages, empty searches) are **fork responsibilities**—the architecture reserves explicit refusal / “insufficient data” paths rather than hallucination.

**Where are the trust boundaries in your system, and how are they enforced?**  
1. **OpenEMR session boundary** — every agent turn starts from validated **session cookies** (PHP probe) and/or **Bearer** (`/apis/{site}/api/user`), or a **demo** role when explicitly enabled; enforced in [`agent/http/deps.py`](agent/http/deps.py) + [`agent/access/openemr_auth.py`](agent/access/openemr_auth.py).  
2. **Role → tool boundary (RBAC)** — enforced before clinical retrieval in the agent layer per [`USERS.md`](USERS.md) Part 2 / `rbac.py`.  
3. **Generation → user boundary** — verification gate + explicit **`verified`** bit; enforced in RGV pipeline + response schema.  
4. **Logging boundary** — structured `agent_event` lines must not echo raw tokens; refusal and auth paths tested for shape (see observability tests).

---

### Your Evaluation

**What does your eval suite test that a happy-path demo would not reveal?**  
It stress-tests **auth and misuse** (missing / wrong headers, OpenEMR misconfiguration), **RBAC denials** (forbidden tool paths with logging contracts), **RGV ordering and bounded retry**, **verify exhaustion** (`verified: false` after retries), **HTTP validation** (422 on empty chat fields), **OpenEMR JSON edge cases** (non-200, invalid JSON, non-object payloads) via httpx mocks, **deploy/offline** Fly manifest assumptions, and **observability fields** on log records—not just “one successful chat POST.”

**What did you find when you ran it?**  
On a typical offline run the suite reports on the order of **~169 passed**, **~15 skipped** (live OpenEMR E2E, optional latency/eval gates, etc.—exact counts drift; see [`README.md`](README.md) and [`.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md`](.planning/eval-artifacts/2026-05-01-submission-prep-snapshot.md)). **Finding:** the **contracts hold** under test, but **skips** are a deliberate reminder of what is **not** continuously proven in CI (real PHI session behavior, real FHIR latency).

**What would you add to it next?**  
- **Fixture-backed FHIR** golden files per role (read-only) with expected retrieve snapshots.  
- **Adversarial prompts** (injection, cross-patient ID attempts) tied to USERS use cases.  
- **SLO tests** (p95 retrieve + generate) behind a staging gate, not every PR.  
- **Regression pack** for “partial grounding” once the verify module exists on the fork.

---

### Production Thinking

**How would you scale this to a 500-bed hospital with 300 concurrent clinical users?**  
Horizontally scale **stateless agent** replicas behind a load balancer; add **per-tenant / per-department rate limits** and **circuit breakers** to OpenEMR FHIR so spikes don’t stampede the EMR; use **read replicas or cached FHIR bundles** for hot chart slices where policy allows; **shard** observability (structured logs + traces) to a queryable backend; separate **interactive** chat from **batch** jobs (summarization queues). Affinity or session stickiness is only needed where server-side conversation state exists—here much state is client-carried `messages`, but OpenEMR and DB still become the bottleneck.

**What would you need to change before you'd be comfortable with a real physician relying on this?**  
Ship **record-backed attribution** for factual claims, **clinically reviewed verify rules**, **SLO + on-call** playbooks, **malpractice / compliance sign-off**, **human-in-the-loop** default for high-risk classes (orders, new diagnoses), **telemetry on cost and tokens**, and **proven rollback** (feature flag / kill switch for the copilot). The current scaffold is **not** that product.

**What failure mode worries you most, and why?**  
**Silent wrong medical “fact” presented as trustworthy**—because verification and UI copy can be misread as “the system checked it” even when `verified` is false or when attribution is incomplete. A close second is **privilege escalation through the copilot** (ADMIN or nurse path accidentally surfacing physician-only context)—RBAC mistakes are subtle and high-impact, which is why they are both **documented** and **tested** early.

---

## 11. How to refresh this document

1. Run `python -m pytest agent/tests deploy/tests -q` and note **passed / skipped**.  
2. Re-read [`.planning/STATE.md`](.planning/STATE.md) and [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for phase completion.  
3. Update **§5 Evaluation** counts and **[`EVAL.md`](EVAL.md)** (53 core + 21 edge-case) if files under `agent/tests/eval/` change; align **§6** if cost tables are filled.  
4. If **users/use cases** change, edit [`USERS.md`](USERS.md) Part 1 first, then summarize here.  
5. If **dependencies or platforms** change, update **§2** and `requirements.txt` / `deploy/requirements-agent.txt` / `chat-ui/package.json` pointers.  
6. If **audit findings, architecture behavior, or eval results** change materially, revise **§10** (interview Q&A) so spoken answers match evidence.  
7. Append **§ Revision history** with date and one-line summary.

---

## Revision history

| Date | Changes |
| --- | --- |
| 2026-05-02 | Initial `PROJECT-SHOWCASE.md`: architecture, users, eval, cost, observability, hygiene pointers; living-doc process. |
| 2026-05-02 | Added **§2 Tools, software, and platforms** (stack tables + rationale); renumbered sections; refresh checklist includes stack updates. |
| 2026-05-02 | Added **§10 Interview-style Q&A** (audit, architecture, evaluation, production thinking); **§11** refresh checklist. |
| 2026-05-02 | Documented **synthetic CSV fixtures** (`fixtures/sample-patients/`), validation script, gitignored `local/`, README + showcase hygiene links. |
| 2026-05-03 | **§11:** Refresh checklist ties evaluation counts to [`EVAL.md`](EVAL.md) when `agent/tests/eval/` changes. |
| 2026-05-02 | Nondisruptive backlog: `CHANGELOG.md`, `MAINTAINERS` routing, `CONTRIBUTING` synthetic data note, pre-commit fixture quick hook, GitHub/GitLab manual full FK jobs, fixture header tests, `deploy/README-fly-agent` link to fixtures. |
