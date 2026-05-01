# AI cost analysis (Gauntlet deliverable)

**Last updated:** 2026-05-01  
**Scope:** Clinical Co-Pilot agent (LLM + retrieval + verification stack). Numbers below mix **measured dev spend** (fill in) and **modeled production** tiers. Replace **TBD** with your billing exports before submission.

---

## 1. Development spend (actual)

| Period | Item | Amount (USD) | Evidence / notes |
| --- | --- | --- | --- |
| TBD | OpenAI / Anthropic API (dev keys) | TBD | Paste invoice or dashboard export |
| TBD | Fly.io (agent + OpenEMR apps) | TBD | `fly scale`, bandwidth, volume |
| TBD | Other (CI, Langfuse host, etc.) | TBD | |

**Total dev (YTD):** TBD

---

## 2. Production model (assumptions)

Document your assumptions so reviewers can challenge them:

| Assumption | Value | Source |
| --- | --- | --- |
| Avg input tokens / chat turn | TBD | logs or staging sample |
| Avg output tokens / chat turn | TBD | same |
| Turns per active clinician / day | TBD | product guess or pilot |
| Active clinicians @ scale tier | see §3 | scenario |
| Verification retries / turn | ≤1 extra generate (see `MAX_VERIFY_RETRIES`) | code |

**Cost formula (illustrative):**  
`monthly_llm_usd ≈ (users × turns × (tok_in + tok_out) / 1e6) × blended_price_per_1M_tokens`  
Add **fixed** Fly machines, DB, egress, and observability hosting separately—do **not** scale those linearly with token count alone.

---

## 3. Tiered projections (illustrative table — replace with your math)

| Monthly active clinicians (MAC) | Rough architecture implication | LLM order-of-magnitude* | Non-LLM infra notes |
| --- | --- | --- | --- |
| **100** | Single-region Fly agent; shared-cpu OK; minimal cache | $ | Low egress; one OpenEMR instance |
| **1,000** | Agent horizontal scale; rate limits; consider prompt caching | $$ | DB read replicas or FHIR proxy tuning |
| **10,000** | Dedicated LLM routing; queue / batch for non-interactive jobs; stronger observability budget | $$$ | Multi-region or failover; audit log retention |
| **100,000** | Enterprise LLM contract; possibly regional inference; strict quotas per org | $$$$ | Compliance, separate staging/prod, SOCs |

\* **Order-of-magnitude only** until you plug **TBD** tokens and vendor pricing.

---

## 4. Architectural changes by tier

- **100 → 1K:** Enable **request budgets** per session; **cache** repeated retrieve payloads; verify-node stays synchronous but **timeouts** tightened.
- **1K → 10K:** Introduce **async** heavy retrieval where safe; **rate limit** per role/org; **multiple agent instances** behind Fly or LB; LLM **routing** (small vs large model).
- **10K → 100K:** **Regional** deployments to cut latency; **reserved capacity** with provider; **evaluation** continuous + shadow traffic; possible **batch summarization** off critical path.

---

## 5. Honesty checklist (submission-quality)

- [ ] Replace all **TBD** with numbers or cite why unknown.
- [ ] Separate **variable** (tokens) vs **fixed** (machines, DB) costs.
- [ ] Mention **verification retries** as a hidden multiplier on generation cost.
- [ ] Align narrative with [`ARCHITECTURE.md`](ARCHITECTURE.md) and `.planning/ROADMAP.md` (scaffold vs fork).

---

## 6. Repo pointers

- Scaffold marks **`cost_envelope="unknown"`** in chat-turn logs until wired (`agent/services/chat_turn.py`).
- Optional latency gate: `RUN_LATENCY_GATE` tests if enabled.
- Fly sizing: `fly.agent.toml` VM memory / CPU.
