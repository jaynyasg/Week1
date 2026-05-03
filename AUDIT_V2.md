# Clinical Co-Pilot — Consolidated Audit Summary (AUDIT_V2.md)

**AgentForge · Gauntlet AI**
**Sources:** [AUDIT.md](AUDIT.md) v1.2, [USERS.md](USERS.md), [ARCHITECTURE.md](ARCHITECTURE.md)

This is a one-page consolidation of the full audit, the users addressed by the system, and the architecture plan. For full evidence and remediation tracking, see [AUDIT.md](AUDIT.md).

**Delta (2026-05-03):** The repo now ships a **FastAPI scaffold** with [`agent/access/rbac.py`](agent/access/rbac.py), **session probe + Bearer + demo** auth paths ([`agent/access/openemr_auth.py`](agent/access/openemr_auth.py), [`deploy/copilot_session_probe.php`](deploy/copilot_session_probe.php)), **five** OpenAI clinical tools ([`agent/tools/dispatch.py`](agent/tools/dispatch.py)), an embedded **React/Vite** UI, and **behavioral evals** ([`EVAL.md`](EVAL.md) — **53 + 21** tests). Treat earlier audit language implying **no `rbac.py`** as **superseded** for this snapshot; **AUD-004 / AUD-005 / Word drift** remain open until runtime evidence exists.

---

## 1. Key audit findings (13 total)

### Critical (2)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-001** | `users.md` contradicted PRD on `ADMIN` permissions. | **Resolved (docs)** — [USERS.md](USERS.md) aligned 2026-04-28. Code in PR #12 still pending. |
| **AUD-013** | Word `Clinical_CoPilot_TaskList_v2.docx` (v2.0) specifies 7 tools and lets NURSE access `labs`, contradicting v1.1 (8 tools, NURSE blocked from `labs`). Following the Word task list would break the RBAC gate. | **Open** |

### High (4)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-002** | Nurse "write notes" semantics contradicted MVP read-only matrix. | **Resolved (docs)** — nurse is read-only subset. |
| **AUD-004** | RBAC for nurse depends on correct FHIR `Observation.category` tagging (`laboratory` vs `vital-signs`); untagged data could leak labs through the vitals tool. | **Open** — gate PR #07. |
| **AUD-005** | ≤5s pre-visit summary budget unproven against real OpenEMR FHIR latency. | **Open** — measure after deploy. |
| **AUD-012** | Word PRD v1.0 diverges materially from markdown v1.1 (10 vs 11 features, different PCP IDs, different HIPAA framing). | **Open** |

### Medium (5)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-003** | PRD §2 Definitions still says "7 patient context functions" while Feature 4 defines 8 tools. | **Open** |
| **AUD-006** | Verification threshold for partial unverifiable claims undecided ("strip + count" vs "withhold all"). | **Open** — pre PR #11. |
| **AUD-007** | Session-keying model (token + patient_id vs server session store) is open. | **Open** — pre PR #08–09. |
| **AUD-008** | Anthropic usage without BAA is acceptable only under demo-data policy. | **Open** — standing until real PHI. |
| **AUD-010** | PCP-10 (multi-patient schedule summary) requires different authorization pattern; cross-patient leakage hazard if built early. | **Waived** — deferred per PRD. |

### Low (2)

| ID | Finding | Status |
|----|---------|--------|
| **AUD-009** | Langfuse self-hosted vs cloud affects compliance narrative. | **Open** — PR #13. |
| **AUD-011** | Deliverable file naming (`USERS.md` / `ARCHITECTURE.md` at repo root). | **Open** — before submission. |

### Critical scope caveat

The audit is **design / document-only**. No runtime security testing, log sampling, or FHIR benchmarks have been run. Findings are not substitutes for runtime security testing, PHI log sampling, or API abuse testing against a live deployment.

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
- **8 patient-context tools:** 7 FHIR (`demographics`, `medications`, `labs`, `vitals`, `allergies`, `problem_list`, `visit_notes`) + 1 REST (`schedule`). Labs/vitals are deliberately split tools on the same `Observation` resource so RBAC can grant vitals without labs.
- **Verification:** programmatic — `grounding.py` (source attribution) + `domain_rules.py` (allergy / lab range / date logic). No LLM-as-judge.
- **RBAC:** `rbac.py` enforced at the **retrieve node**; refusals named and logged.
- **Observability:** Langfuse self-hosted; spans from all 3 graph nodes; `/flag` writes FLAG events without re-generation.

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
| Vitals/labs split | Two FHIR tools on one Observation resource (category filter) | NURSE can access vitals without labs; RBAC requires distinct tool identities |
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

The design is internally strong on the non-negotiables: session scoping to a single patient, programmatic verification, graceful degradation, and no PHI on disk. The RBAC story is now documentation-consistent. Three open issues — `Observation` category tagging (AUD-004), FHIR latency proof (AUD-005), and Word-export drift (AUD-012 / AUD-013) — must close with measured evidence before code-level audits can take over from this static review.
