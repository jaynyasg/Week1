# AI cost analysis (Gauntlet deliverable)

**Last updated:** 2026-05-03  
**Scope:** Clinical Co-Pilot agent (LLM + retrieval + verification stack).

This document now includes **modeled USD** from public **list prices** and explicit token assumptions. **Your actual bill** = usage × those rates (plus taxes / tiers). Replace **TBD** in §1 with exports from your OpenAI and Fly dashboards before a formal submission.

**Primary API model in this repo:** [`OPENAI_CHAT_MODEL`](agent/services/openai_tool_loop.py) defaults to **`gpt-4o-mini`** when unset.

---

## 1. Development spend (actual)

| Period | Item | Amount (USD) | Evidence / notes |
| --- | --- | --- | --- |
| TBD | OpenAI / Anthropic API (dev keys) | TBD | Paste invoice or dashboard export |
| TBD | Fly.io (agent + OpenEMR apps) | TBD | `fly scale`, bandwidth, volume |
| TBD | Other (CI, Langfuse host, etc.) | TBD | |

**Total dev (YTD):** TBD

---

## 2. Vendor list prices (snapshot for math below)

Rates below are **OpenAI public list prices** (USD per **1M tokens**) as commonly published for chat models in 2026; **confirm** on [OpenAI Pricing](https://openai.com/api/pricing/) before locking a budget. Cached-input discounts are omitted unless you enable prompt caching.

| Model | Input $/1M | Output $/1M | Notes |
| --- | ---: | ---: | --- |
| **gpt-4o-mini** | 0.15 | 0.60 | Default in scaffold; best baseline for tables below |
| **gpt-4o** | 2.50 | 10.00 | “Step up” if quality/latency requires a larger model |

**Formula for one completion:**  
`usd = (tokens_in / 1e6) × price_in + (tokens_out / 1e6) × price_out`

**Tool-loop note:** With [`AGENT_LLM_CSV_TOOLS=1`](agent/services/openai_tool_loop.py), each **tool round** is typically a **separate** Chat Completions call until the model returns final text (cap `_MAX_TOOL_ROUNDS = 10`). **Billable tokens** accumulate across rounds (system prompt and history are re-sent per request unless you optimize). **Verification** can add up to **one extra generate** pass ([`MAX_VERIFY_RETRIES = 1`](agent/runtime/rgv_pipeline.py)) on failure paths.

---

## 3. Example token assumptions (for illustration)

These are **not** measured from production logs; they are **reasonable ranges** for a short clinician question with one chart context.

| Scenario | Completions (calls) | Total input tok (all calls) | Total output tok (all calls) | Rationale |
| --- | ---: | ---: | ---: | --- |
| **A — Simple reply** (no tool path / echo path or single completion) | 1 | 900 | 350 | System + 1 user turn + moderate reply |
| **B — Typical tools** (2 model rounds: plan/tools → answer) | 2 | 6,500 | 600 | Larger system + tool defs; one tool result blob |
| **C — Heavy tools + retry** (2 rounds + one verify failure → regen) | 3 | 9,500 | 900 | Extra history + second answer attempt |

Adjust these after you log **real** `usage.prompt_tokens` / `completion_tokens` from OpenAI.

---

## 4. Worked per-turn cost (list price only)

| Scenario | **gpt-4o-mini** | **gpt-4o** |
| --- | ---: | ---: |
| A — Simple | **≈ $0.00035** | **≈ $0.0058** |
| B — Typical tools | **≈ $0.00134** | **≈ $0.0223** |
| C — Heavy + retry | **≈ $0.00196** | **≈ $0.0328** |

**Mini — scenario B detail:**  
`(6,500 / 1e6)(0.15) + (600 / 1e6)(0.60) = 0.000975 + 0.00036 ≈ $0.00134` per **successful** multi-round turn (single verify pass).

---

## 5. Monthly LLM-only rollups (illustrative)

Assume **22 clinical days / month**, **20 co-pilot turns / day / clinician**, all at **scenario B** mix.

| MAC | Turns / month | gpt-4o-mini (@ $0.00134) | gpt-4o (@ $0.0223) |
| --- | ---: | ---: | ---: |
| 10 | 4,400 | **≈ $6** | **≈ $98** |
| 100 | 44,000 | **≈ $59** | **≈ $981** |
| 1,000 | 440,000 | **≈ $590** | **≈ $9,810** |

If half of turns are **scenario A** and half **scenario B**, blend costs:  
`0.5 × $0.00035 + 0.5 × $0.00134 ≈ $0.00085` / turn on mini → 44,000 turns ≈ **$37/mo** at 100 MAC.

**Behavioral evals** ([`EVAL.md`](EVAL.md), 53 + 21 tests) run **mocked** in CI by default: **~$0** LLM spend for that suite.

---

## 6. Non-LLM infra (order of magnitude)

| Item | Rough monthly USD | Notes |
| --- | ---: | --- |
| Agent VM (Fly) | **~$3–15** | [`fly.agent.toml`](fly.agent.toml): `shared-cpu-1x`, `512mb`; depends on region, always-on vs scale-to-zero, and egress |
| OpenEMR host | **varies** | Often dominates vs agent LLM at small MAC |
| Observability (Langfuse, etc.) | **$0–50+** | Self-host vs cloud |

FHIR/REST traffic to OpenEMR does not hit OpenAI’s meter but drives **EHR load, egress, and SRE time**.

---

## 7. Tiered projections (architecture vs cost)

| MAC | Rough architecture implication | LLM (mini, scenario B order-of-mag.) | Non-LLM notes |
| --- | --- | ---: | --- |
| **100** | Single-region Fly agent; shared CPU | **~$50–80/mo** at 20 turns/day (see §5) | Low egress; one OpenEMR instance |
| **1,000** | Horizontal scale; rate limits; prompt / retrieve cache | **~$0.5–1k/mo** same usage | DB / FHIR tuning |
| **10,000** | Queues, routing small vs large model, strong observability | **~$5–10k/mo** before enterprise discounts | Multi-region, audit retention |

\* Recompute with **your** token histogram; **large-model** rows scale ~**17×** vs mini for the same tokens (price ratio at list rates).

---

## 8. Architectural changes by tier

- **100 → 1K:** Enable **per-session budgets**; **cache** stable system + tool preamble; tighten **timeouts** on verify.
- **1K → 10K:** **Rate limit** per org; **multiple** agent machines; **route** cheap vs premium model by intent.
- **10K → 100K:** **Enterprise** API pricing; **regional** inference; **continuous eval** + shadow traffic.

---

## 9. Honesty checklist (submission-quality)

- [ ] Replace §1 **TBD** with invoice-backed spend or label as “not tracked.”
- [ ] Log **real** token usage for 100–500 prod/staging turns and replace §3 assumptions.
- [ ] Separate **variable** (tokens) vs **fixed** (machines, DB) costs — §5 vs §6.
- [ ] Mention **tool rounds** and **verify retries** as multipliers ([§2](#2-vendor-list-prices-snapshot-for-math-below)).
- [ ] Align narrative with [`ARCHITECTURE.md`](ARCHITECTURE.md) and `.planning/ROADMAP.md`.

---

## 10. Repo pointers

- Scaffold marks **`cost_envelope="unknown"`** in chat-turn logs until wired ([`agent/services/chat_turn.py`](agent/services/chat_turn.py)).
- Optional latency gate: `RUN_LATENCY_GATE` tests if enabled.
- Fly sizing: [`fly.agent.toml`](fly.agent.toml) VM memory / CPU.
- **Behavioral eval footprint (CPU-only):** [`EVAL.md`](EVAL.md) — 53 + 21 tests; no token spend in mocked runs.
