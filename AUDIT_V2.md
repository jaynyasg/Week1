# Clinical Co-Pilot — Consolidated Audit Summary (AUDIT_V2.md)

**AgentForge · Gauntlet AI**  
**Sources:** [AUDIT.md](AUDIT.md) v1.3, [USERS.md](USERS.md), [ARCHITECTURE.md](ARCHITECTURE.md)

This is a one-page consolidation of the full audit, the users addressed by the system, and the architecture plan. For full evidence and remediation tracking, see [AUDIT.md](AUDIT.md) §4–§6.

**Delta (2026-05-03):** The repo ships a **FastAPI scaffold** with [`agent/access/rbac.py`](agent/access/rbac.py), **session probe + Bearer + demo** auth paths ([`agent/access/openemr_auth.py`](agent/access/openemr_auth.py), [`deploy/copilot_session_probe.php`](deploy/copilot_session_probe.php)), **five** OpenAI clinical tools ([`agent/tools/dispatch.py`](agent/tools/dispatch.py)), **FHIR Observation category filtering** ([`agent/tools/openemr_fhir.py`](agent/tools/openemr_fhir.py)), an embedded **React/Vite** UI, [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md) for Word-vs-markdown authority, and **behavioral evals** ([`EVAL.md`](EVAL.md) — **53 + 21** tests).

---

## 1. Key audit findings (13 total) — May 2026 snapshot

### Critical (2)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-001** | `users.md` contradicted PRD on `ADMIN` permissions (historical). | **Resolved** — [`USERS.md`](USERS.md) + [`rbac.py`](agent/access/rbac.py) + tests |
| **AUD-013** | Word TaskList v2.0 contradicts v1.1 nurse RBAC (nurse/`labs`, seven tools). | **Governance resolved (Week1)** — [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md); do not implement from Word without diff |

### High (4)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-002** | Nurse “write notes” vs MVP read-only matrix (historical). | **Resolved** (docs) |
| **AUD-004** | Nurse vitals vs labs depends on FHIR `Observation.category`. | **Mitigated** — in-process category code filter + `skipped_not_matching_category`; uncategorized rows omitted |
| **AUD-005** | ≤5s pre-visit summary budget unproven vs real FHIR latency. | **Partial** — run [`scripts/benchmark_fhir_latency.py`](scripts/benchmark_fhir_latency.py); record p50/p95 in next [AUDIT.md](AUDIT.md) revision |
| **AUD-012** | Word PRD v1.0 diverges from markdown v1.1. | **Governance resolved (Week1)** — [`DOCUMENT-CONTROL.md`](DOCUMENT-CONTROL.md) |

### Medium (5)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-003** | “7 patient context functions” vs eight tools. | **Resolved (in-repo PRD + USERS)**; external `AF/PRD.md` may still need an edit |
| **AUD-006** | Verification threshold for partial unverifiable claims undecided. | **Partial** — scaffold: `verified` + bounded retry; fork owns strip/withhold ADR ([`ARCHITECTURE.md`](ARCHITECTURE.md)) |
| **AUD-007** | Session-keying model open. | **Resolved (scaffold)** — stateless API; `patient_id` + `X-Clinical-Session-Id` ([`ARCHITECTURE.md`](ARCHITECTURE.md)) |
| **AUD-008** | LLM vendor without BAA only under demo-data policy. | **Standing** — prod PHI requires BAAs + operator review |
| **AUD-010** | PCP-10 multi-patient schedule — cross-patient hazard. | **Waived** — deferred per PRD |

### Low (2)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-009** | Langfuse self-hosted vs cloud — compliance narrative. | **Partial** — [`.planning/observability-gap-analysis.md`](.planning/observability-gap-analysis.md) |
| **AUD-011** | Deliverable file naming (`USERS.md` / `ARCHITECTURE.md`). | **Resolved** — present at repo root |

### Scope caveat

The **April 2026** audit pass was static for external `AF/*` artifacts. The **Week1** codebase adds **enforcement and tests**, but findings are **not** substitutes for penetration testing, PHI log sampling, or production FHIR load results. See [AUDIT.md](AUDIT.md) v1.3.

---

## 2. Users addressed (RBAC matrix)

Three roles, enforced at the **agent layer** (e.g. retrieve node → `rbac.py`) — not UI-only.

| Tool | PHYSICIAN | NURSE | ADMIN |
|------|-----------|-------|-------|
| `demographics` | ✓ | ✓ | ✓ |
| `problem_list` | ✓ | ✗ | ✗ |
| `medications` | ✓ | ✓ | ✗ |
| `labs` | ✓ | ✗ | ✗ |
| `vitals` | ✓ | ✓ | ✗ |
| `allergies` | ✓ | ✓ | ✗ |
| `visit_notes` | ✓ | ✗ | ✗ |
| `schedule` | ✓ | ✓ | ✓ |

### Role flows

- **PHYSICIAN** — all 8 tools, single-patient session-scoped. Still subject to verification (grounding + domain rules); RBAC does not bypass safety checks.
- **NURSE** — 5 read-only tools (`demographics`, `medications`, `vitals`, `allergies`, `schedule`). Blocked from `labs`, `visit_notes`, `problem_list`. Refusal must name **role + tool** and be logged.
- **ADMIN** — security boundary, **not** a co-pilot persona. Only `demographics` + `schedule`. All clinical tools refused. Designed to prevent privilege escalation through the co-pilot, even though OpenEMR-native admin has broader rights.

### Refusal behavior (required)

1. Return a clear message naming both role and tool (e.g. role NURSE cannot run tool `labs`).
2. Log: role, tool, hashed identifiers per observability policy (PRD Feature 10).
3. Do not return partial clinical data from that tool via side channels.

---

## 3. Architecture plan

### Topology

Browser → Nginx (TLS termination) → two services in one Docker network on Fly.io / Railway:

- **OpenEMR (PHP / Apache)** — chart UI, `copilot_panel.php` injects the chat widget, exposes FHIR R4 + REST.
- **Agent microservice (FastAPI / Python 3.11)** — separate service. **Auth:** clinician session via **PHP session probe** (cookie), **Bearer** token validated against OpenEMR `/apis/{site}/api/user`, or **demo bypass** when configured — see [`.planning/AI-ARCHITECTURE.md`](.planning/AI-ARCHITECTURE.md) and [`agent/access/openemr_auth.py`](agent/access/openemr_auth.py).

### Agent internals

- **API layer:** `POST /chat`, `/summary`, `/flag`, `GET /chat/stream` (SSE) → Auth middleware → PHI-safe logger → `AgentState` (patient_id, role, session_id, messages, tool_results, verified).
- **LangGraph state machine:** Retrieve → Generate → Verify, with ≤1 retry on verify failure.
- **8 patient-context tools (target):** 7 FHIR + 1 REST (`schedule`). **Shipped scaffold:** five OpenAI tools (demographics, medications, labs, vitals, allergies) — see [`dispatch.py`](agent/tools/dispatch.py).
- **Verification:** programmatic — `grounding.py` (source attribution) + `domain_rules.py` (allergy / lab range / date logic). No LLM-as-judge.
- **RBAC:** `rbac.py` enforced at the **retrieve node**; refusals named and logged.
- **Observability:** Langfuse self-hosted (target); scaffold: structured `agent_event` logs.
- **FHIR labs/vitals:** server query + **client-side category code filter** to mitigate miscategorized `Observation` resources.

### Key architecture choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent placement | Separate FastAPI microservice in same Docker network | Keeps Python/AI code cleanly separated from OpenEMR PHP; communicates via FHIR/REST API |
| Data access | FHIR R4 primary, direct MySQL fallback | FHIR is the standard; some resources (e.g. appointments) require REST |
| Auth flow | **Cookies** → PHP session probe; **Bearer** → `/apis/{site}/api/user`; optional **demo bypass** (env + header) | Covers embedded UI, API clients, and non-PHI demos without a second clinician login |
| LLM | Claude Sonnet (Anthropic) | Context window, reliable JSON, best instruction following for clinical structured output |
| Agent framework | LangGraph | Explicit state for multi-turn sessions; retrieve → generate → verify with retry |
| Verification | Programmatic grounding + domain rules | Faster than LLM-as-judge; deterministic; catches hallucinations and clinical constraint violations |
| Observability | Langfuse (self-hosted) | HIPAA-compatible; full trace visibility across all LangGraph nodes |
| Frontend | **React + TypeScript + Vite** embedded at `/interface/copilot/`; Apache proxies `/agent` to FastAPI | Same-origin cookies for session auth; optional standalone Fly app for the SPA |
| Vitals/labs split | Two FHIR tools on one Observation resource (category filter + in-process enforcement) | NURSE can access vitals without labs; RBAC requires distinct tool identities |
| Session scoping | `AgentState` bound to one `patient_id`; navigation change resets state | Prevents context bleed between patients |
| Incorrect-response flagging | `POST /flag` writes a FLAG event to Langfuse; no re-generation | Audit trail; auto-correction is out of scope for v1 |
| Graceful degradation | Frontend shows "Co-Pilot unavailable" banner when agent is unreachable | Clinicians can still use OpenEMR; agent failure must not block core EHR workflows |

### PRD feature → architecture → task trace

| PRD feature | Architecture anchor | Tasks PR |
|-------------|---------------------|----------|
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

## 4. Bottom line

Most **documentation and governance** findings are **resolved or mitigated in this repository** ([AUDIT.md](AUDIT.md) v1.3): RBAC code + evals, Observation category defense-in-depth, document control for Word drift, root deliverable names, and a **repeatable FHIR latency script**. **Still operator-owned:** paste benchmark numbers (AUD-005), production security testing, PHI log review, Langfuse deployment mode under real compliance constraints (AUD-008/009), and final verify policy for partial grounding in the fork (AUD-006).
