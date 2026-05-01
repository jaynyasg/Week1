# Primary user and use cases (Gauntlet deliverable)

This document names the **primary user** the Clinical Co-Pilot is designed for and lists **concrete use cases** that justify multi-turn conversation, tool use, and verification. It complements the **tool/RBAC matrix** in [`USERS.md`](USERS.md) (role-to-tool access) and the system design in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Primary user

**Dr. Sam Rivera** — a board-certified family physician (or internist) working in an **ambulatory** OpenEMR deployment. They live inside the chart during **15–20 minute** visits: reviewing problems, medications, recent labs and vitals, and visit notes before making a decision. They are comfortable with the EHR but **time-poor**; they need answers that are **grounded in the chart**, not generic LLM advice. They work under **scope-of-practice** and **documentation** norms: if the copilot states a fact about the patient, it must be **attributable** to data they could plausibly have seen in that session (labs, notes, meds, etc.).

This persona is the default **PHYSICIAN** path in the agent RBAC model. Nurses, front-desk, and admin workflows are out of scope for *this* user doc except where **separation of duties** (e.g. vitals without labs) appears as a **safety requirement** in [`USERS.md`](USERS.md).

---

## Use case index (traceability)

Each use case below maps to **multi-turn** and/or **tool-backed** behavior required by the product. If a capability cannot be tied here, it should not ship as part of the core agent.

| ID | Use case | Why multi-turn? | Why tools / verification? |
|----|----------|-----------------|----------------------------|
| **UC-01** | **Pre-visit chart priming** — “What changed since last visit for this patient?” | Follow-up: “Show only diabetics-relevant changes” / “What about medications?” | Needs aggregated chart context (problems, meds, recent labs/notes); answers must not invent changes. |
| **UC-02** | **Medication reconciliation assist** | Clinician asks “What’s interacting with X?” after an initial list | Tool-backed med + problem data; verify claims against retrieved records. |
| **UC-03** | **Lab trend explanation** | User asks for clarification on *which* lab and *when* | Retrieves `Observation` history; verification ensures numeric/time claims match sources. |
| **UC-04** | **Visit summary draft (grounded)** | Iterative: shorten, then add coding-oriented phrasing | Multi-turn editing; every sentence must remain tied to note/lab sources or be explicitly marked uncertain. |
| **UC-05** | **Role-appropriate triage (negative path)** | N/A (single turn may suffice) | **NURSE** or **FRONT** must be **refused** clinical depth per [`USERS.md`](USERS.md); tests cover unauthorized access patterns. |

---

## Out of scope (for this persona, v1)

- **Order entry** and **signing** orders in the EHR.
- **Billing-optimized** documentation without clinical review.
- **Population health** across many patients in one session (co-pilot is **chart-scoped** per session design in [`ARCHITECTURE.md`](ARCHITECTURE.md)).

---

## How this repo uses this file

- **In-repo agent** (this Week1 repository): implements **HTTP contracts**, **scaffold** retrieve–generate–verify, **OpenEMR session validation**, and **tests** that prove ordering, multi-turn carry-over, and verification *fields* on responses.  
- **Full record-backed attribution in natural language** and **production LLM + FHIR** paths are **fork / deployed-stack** work, as described in [`.planning/ROADMAP.md`](.planning/ROADMAP.md) and [`.planning/AI-ARCHITECTURE.md`](.planning/AI-ARCHITECTURE.md).

When the fork adds real tools, each new tool should cite at least one **UC-*** id in its design note or PR description.
