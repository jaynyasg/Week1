# Phase 6 Execution Plan — Documentation Governance Cleanup

## Objective
Eliminate **markdown-vs-Word drift** by making **`.planning/` markdown** the single authoritative surface for requirements and decisions, with explicit **traceability** so ADR/SPEC IDs and history cannot be silently overwritten.

## Non-Goals
- Replacing Phase 5 evaluation harnesses or Phase 4 telemetry contracts.
- Full content rewrite of legacy Word narratives beyond reconciliation or explicit non-authoritative marking.

## Current Baseline (Week1 repo)
- Roadmap Phase 6 success criteria and `SAFE-canonical-markdown-governance` define canonical markdown, Word reconciliation, and traceability; this stub sequences governance work against those outcomes without prescribing automation tooling yet.

## Work Items
1. **Canonical markdown statement** — Add or update repository governance (e.g. `CONTRIBUTING`, project rules, or `.planning/` README pointer) stating **markdown in `.planning/` is authoritative over Word exports** for planning and requirements.
2. **Word artifact inventory** — List divergent Word copies (paths, owners); for each, **reconcile to markdown** or **mark non-authoritative** with a dated note and link to canonical source.
3. **Markdown authoring rules** — Document how new/updated planning docs stay in markdown (no silent “export replaces truth” workflow).
4. **Traceability IDs** — Require stable IDs on ADR/SPEC/decision blocks; define how merges and edits preserve IDs and change history (no silent overwrite of locked decisions).
5. **Review checkpoint** — Lightweight checklist: canonical statement present, inventory closed or explicitly deferred with rationale, traceability spot-check on recent edits.

## Exit Criteria (requirement IDs)
| ID | Done when |
|----|-------------|
| `SAFE-canonical-markdown-governance` | Governance states markdown `.planning/` artifacts are canonical over Word; divergent Word is reconciled or marked non-authoritative; planning updates preserve traceability IDs and do not silently overwrite ADR/SPEC decisions. |

## Suggested Order
1. Canonical markdown + authoring rules in repo docs.
2. Inventory → reconcile or mark non-authoritative per item.
3. Traceability conventions + spot-check against recent changes.

## Repo evidence (scaffold)
- **Planning root**: `.planning/` is the repository’s canonical planning directory (roadmap, state, requirements, plans, intel, ingest outputs).
- **ROADMAP**: Present at `.planning/ROADMAP.md`.
- **STATE**: Present at `.planning/STATE.md`.
- **REQUIREMENTS**: Present at `.planning/REQUIREMENTS.md` (separate `requirements.md` also exists under `.planning/intel/`).
- **Ingest artifacts**: `.planning/ingest/` exists with `synthesis.json` and per-document JSON under `.planning/ingest/classifications/`; `.planning/INGEST-CONFLICTS.md` cites multiple paths under `.planning/ingest/classifications/`.
- **Word vs markdown (verified)**: `.planning/PROJECT.md` § *Canonical Source Policy* states that markdown artifacts in the repository are canonical and that divergent Word exports are non-authoritative and must not override markdown decisions, requirements, or runbooks. `.planning/STATE.md` records the same as a **Canonical policy** bullet (markdown authoritative; divergent Word non-authoritative).
