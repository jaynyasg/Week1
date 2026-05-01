# Eval snapshot — latency & cost (template)

**Checkpoint:** `<milestone or date>`  
**Environment:** `<local | staging | production-like>`  
**Runner:** `<machine / CI job URL>`

## Latency (scaffold or production path)

| Step or endpoint | Samples | p50 / max (ms) | Gate (ms) | Pass / fail |
| --- | ---: | ---: | ---: | --- |
| `POST /agent/chat` (scaffold) | | | | |
| Pre-visit summary (fork) | | | | |

**Command used:** e.g. `RUN_LATENCY_GATE=1 python -m pytest agent/tests/integration/test_latency_gate_optional.py -q`

## Cost (qualitative)

| Driver | Estimate / note | Mitigation |
| --- | --- | --- |
| LLM tokens | | |
| Fly compute | | |
| Data egress | | |

## Sign-off

- Reviewer:
- Date:
