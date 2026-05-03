# AI cost analysis (Gauntlet deliverable)

**Last updated:** 2026-05-03  
**Scope:** Clinical Co-Pilot agent (LLM + retrieval + verification stack).

All dollar amounts below come from **published vendor list prices** (with **arithmetic** for combined scenarios). Your invoice may differ (taxes, prepaid commitments, enterprise discounts, regional Fly rates, actual token usage).

**Primary API model in this repo:** [`OPENAI_CHAT_MODEL`](agent/services/openai_tool_loop.py) defaults to **`gpt-4o-mini`** when unset.

**Authoritative price sources (retrieved for this document):**

- **OpenAI** — Standard API rates: [OpenAI API pricing](https://openai.com/api/pricing/) and model table [Pricing (platform docs)](https://platform.openai.com/docs/pricing) (prices per **1M tokens**).
- **Fly.io** — Machine RAM/CPU: [Fly.io resource pricing](https://fly.io/docs/about/pricing/) (per-second → **730h/mo** “always-on” equivalents in their tables).
- **Langfuse Cloud** — [Langfuse pricing](https://langfuse.com/pricing) (Hobby **$0**, Core **$29/mo**, etc.).
- **GitHub Actions** — [Billing for GitHub Actions](https://docs.github.com/en/billing/concepts/billing-for-github-actions) (public repos: **$0** for standard hosted runners within policy).

---

## 1. Example “small team” month (modeled, not an invoice)

Illustrates how list prices combine. Figures are **rounded**.

| Line item | Amount (USD) | Basis |
| --- | ---: | --- |
| OpenAI **`gpt-4o-mini`** (Standard) | **1.92** | **8M** input + **1.2M** output tokens/month → \((8 × 0.15) + (1.2 × 0.60) = 1.20 + 0.72\) using [platform **gpt-4o-mini** row: **$0.15 / $0.60** per 1M](https://platform.openai.com/docs/pricing) |
| Fly.io **1×** `shared-cpu-1x` **512MB** machine (always-on) | **3.32** | Fly [resource pricing](https://fly.io/docs/about/pricing/) table lists **~$3.32/mo** for that shape in published examples (use their calculator for your region; regions differ slightly) |
| GitHub Actions (CI) | **0.00** | **Public** repo: standard Linux minutes **$0** within [GitHub Actions billing](https://docs.github.com/en/billing/concepts/billing-for-github-actions) allowances |
| Langfuse Cloud **Hobby** | **0.00** | [Langfuse Hobby](https://langfuse.com/pricing): **$0**, 50k billable units/mo cap |
| **Example subtotal** | **~5.24** | Sum of above |

If you add a **second** Fly machine (e.g. OpenEMR on its own VM of the same size), add **~$3.32/mo** from the same Fly table. Volumes are extra (**~$0.15/GB/mo** on Fly per [resource pricing](https://fly.io/docs/about/pricing/)).

---

## 2. OpenAI list prices used in this document (Standard tier)

From [OpenAI platform pricing — Standard](https://platform.openai.com/docs/pricing) (USD per **1M tokens**):

| Model | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| **gpt-4o-mini** | $0.15 | $0.075 | $0.60 |
| **gpt-4o** | $2.50 | $1.25 | $10.00 |

**One completion (uncached):**  
\(\text{usd} = (\text{tokens\_in} / 10^6) × \text{input\_price} + (\text{tokens\_out} / 10^6) × \text{output\_price}\)

**Tool-loop note:** With [`AGENT_LLM_CSV_TOOLS=1`](agent/services/openai_tool_loop.py), each **tool round** is usually a **separate** Chat Completions call until the model emits final text (cap `_MAX_TOOL_ROUNDS = 10`). Tokens sum across rounds unless you use **cached input** ([OpenAI prompt caching](https://platform.openai.com/docs/guides/prompt-caching), **$0.075** / 1M for **gpt-4o-mini** cached). **Verification** can add one extra generate ([`MAX_VERIFY_RETRIES = 1`](agent/runtime/rgv_pipeline.py)).

**Batch API** is **−50%** on those Standard input/output rates for eligible jobs per the same pricing page.

---

## 3. Token scenarios (engineering assumptions)

Reasonable **short** clinician question + light chart context; replace with logged `usage` from OpenAI when available.

| Scenario | Completions | Total input tok | Total output tok |
| --- | ---: | ---: | ---: |
| **A — Simple reply** | 1 | 900 | 350 |
| **B — Typical tools** (two rounds) | 2 | 6,500 | 600 |
| **C — Heavy + verify retry** | 3 | 9,500 | 900 |

---

## 4. Per-turn cost at list price (Standard, uncached)

| Scenario | **gpt-4o-mini** | **gpt-4o** |
| --- | ---: | ---: |
| A | **$0.000345** | **$0.00575** |
| B | **$0.001335** | **$0.02225** |
| C | **$0.001965** | **$0.03275** |

**Mini, scenario B:** \((6500/10^6)(0.15) + (600/10^6)(0.60) = 0.001335\).

---

## 5. Monthly LLM-only rollups

Assume **22 clinical days**, **20 turns/day/clinician**, **scenario B** every turn.

| MAC | Turns/mo | **gpt-4o-mini** @ $0.001335 | **gpt-4o** @ $0.02225 |
| --- | ---: | ---: | ---: |
| 10 | 4,400 | **$5.87** | **$97.90** |
| 100 | 44,000 | **$58.74** | **$979.00** |
| 1,000 | 440,000 | **$587.40** | **$9,790.00** |

**50/50 blend** of scenarios A and B on mini: \((0.5 × 0.000345) + (0.5 × 0.001335) = 0.00084\) / turn → 44,000 turns → **~$36.96/mo** at 100 MAC.

**Behavioral evals** ([`EVAL.md`](EVAL.md)) run **mocked** in CI: **$0** OpenAI meter.

---

## 6. Non-LLM infra (list-price anchors)

| Item | Monthly USD | Source |
| --- | ---: | --- |
| Agent VM (`shared-cpu-1x`, 512MB, always-on) | **~3.32** | [Fly.io resource pricing](https://fly.io/docs/about/pricing/) |
| + second VM (e.g. OpenEMR) same size | **~3.32** | Same |
| Volume 10 GB | **~1.50** | **~$0.15/GB/mo** on Fly ([pricing](https://fly.io/docs/about/pricing/)) |
| Outbound bandwidth | **0–** | First **100 GB/mo** often **$0** on Fly; beyond that **~$0.02/GB** (see Fly docs) |
| **Langfuse Cloud Core** (if used) | **29.00** | [Langfuse Core](https://langfuse.com/pricing) base; + graduated units beyond 100k |
| **Langfuse self-hosted** | **0.00** | Software OSS; you still pay underlying Fly/VM + ops time ([self-hosting](https://langfuse.com/docs/deployment/self-host)) |

FHIR traffic does not bill OpenAI but affects Fly egress and OpenEMR sizing.

---

## 7. Tiered projections (architecture vs cost)

| MAC | Architecture note | LLM (mini, §5 @ 100 MAC) | Non-LLM anchor |
| --- | --- | ---: | --- |
| **100** | Single-region Fly | **~$59/mo** LLM + **~$7** two tiny VMs (Fly table) | Add volumes/egress |
| **1,000** | Scale-out, caching | **~$587/mo** LLM | More machines + DB |
| **10,000** | Routing, queues | **~$5,874/mo** LLM at same per-clinician usage | Enterprise API / reserved capacity |

**Large-model multiplier** at equal tokens: **gpt-4o** output/input list ratio vs mini is \((10/0.6)/(2.5/0.15)\) on output-heavy workloads — roughly **~16–17×** on the scenario-B blend (use §4 columns).

---

## 8. Architectural levers (cost)

- **100 → 1K:** Prompt / system **caching** ([OpenAI cached input](https://platform.openai.com/docs/pricing) **$0.075**/1M for mini); cap tool rounds; **Batch** (−50%) for offline jobs.
- **1K → 10K:** Route cheap vs premium model; **Fly** horizontal scale; Langfuse **spend alerts** ([Langfuse docs](https://langfuse.com/docs/administration/spend-alerts)).
- **10K → 100K:** OpenAI **Scale / reserved** ([OpenAI Scale Tier](https://openai.com/api-scale-tier/)); regional inference per contract.

---

## 9. Repo pointers

- Scaffold may log **`cost_envelope="unknown"`** until wired ([`agent/services/chat_turn.py`](agent/services/chat_turn.py)).
- Optional latency gate: `RUN_LATENCY_GATE` tests if enabled.
- Fly sizing: [`fly.agent.toml`](fly.agent.toml).
- **Evals (CPU-only):** [`EVAL.md`](EVAL.md) — 53 + 21 tests.
