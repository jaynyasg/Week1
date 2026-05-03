# USERS.md — Target users, workflows, use cases, and RBAC

**Hard gate (Stage 4):** This document is the **source of truth** for **who** the Clinical Co-Pilot is for, **how** it enters their real workflow, and **which problems** it solves. [`ARCHITECTURE.md`](ARCHITECTURE.md) and implementation choices **must trace** to the users and use cases defined here—not the other way around.

**Normative RBAC / PRD alignment:** Part 2 matches **PRD v1.1 · Feature 8** (Role-Based Access Control). Enforcement happens at the **agent layer** (e.g. retrieve node → `rbac.py`) so role boundaries are not UI-only.

---

## Part 1 — User profiles and use cases

### 1.1 Design rule: narrow beats generic

“Physicians need help finding information” is **not** a user definition—it is a thesis that has shipped a thousand dead health-tech products. This project **commits to one primary, concrete user** for v1 narrative and product constraints. Other clinician archetypes exist in the world; they are **explicitly out of scope** until we re-run discovery (see §1.8).

### 1.2 Primary user (v1): Dr. Sam Rivera

**Who:** Board-certified **family medicine / general internal medicine** physician in an **ambulatory** practice on **OpenEMR**. Typical load: **~18–22 face-to-face visits per clinic day** (we model **20**), mostly **15-minute slots** with a mix of chronic follow-up, acute complaints, and Medicare wellness visits.

**Environment:** One chart at a time in the browser; cognitive bandwidth is consumed by **medication reconciliation**, **labs trending**, **visit note review**, and **patient counseling**—not by navigating twelve tabs to stitch together context.

**What “useful” means here:**

| Dimension | What this user requires |
| --- | --- |
| **Grounding** | Statements about the patient must be **traceable** to chart data they could review in-session—not plausible clinical textbook gloss. |
| **Latency** | Answers during the visit should feel **dialogue-fast** (seconds to low tens of seconds), not batch-report slow. |
| **Refusal** | When data are missing or role boundaries apply, the copilot must **say so** and narrow scope—not fabricate or quietly omit. |
| **Trust shape** | Output must support **quick correction** (“that’s the wrong med—use the active list”) without forcing a new navigation path in OpenEMR. |

**Why this person constrains the agent:** They are **not** hunting for a novel visualization—they are **compressing decision time** while staying inside safe, auditable chart facts. The agent’s failures (hallucination, overconfidence, role bleed) map directly to **wrong clinical decisions** or **lost trust**, so verification + RBAC are first-class—not polish.

### 1.3 Workflow: the minute the copilot enters the day

**Morning (before first patient, ~8:30–8:45):** Dr. Rivera skims the **schedule** in OpenEMR—not to memorize every chart, but to **sequence worry**. They care most about: new abnormal labs overnight, no-shows to reschedule mentally, and which visits are “heavy” (new diabetes, post-hospital follow-up).

**The thirty seconds before opening the copilot (between rooms):** They have already clicked into **today’s patient chart**. Hands are on history / meds / recent results. What they **do not** want is another dashboard tab to interpret. They want a **single conversational surface** that answers *their next question*, which only emerged **after** reading the first screen—e.g., “Why is creatinine up if they’re not on ACE?” That question is **contextual** and often **follow-up-shaped**.

**During the visit:** The patient is speaking; the physician steals 10–20 second glances to confirm facts (“When was HbA1c last?”). The interface must support **short, precise follow-ups**, not a wall of widgets.

**After the visit (documentation arc):** They may ask the copilot to **reshape** a draft summary or bridge coding-oriented phrasing—**iteratively**, not as a one-shot template—because billing rules and clinical nuance conflict in ways static templates handle poorly.

### 1.4 Use cases (detailed)

Each use case below includes an **explicit defense** of why a **conversational agent** is the right shape—versus a **dashboard**, **sorted list**, **better chart view**, or **static report**.

---

#### UC-01 — Pre-visit chart priming (“what matters *for this visit*)”

- **Workflow anchor:** Patient is roomed; Dr. Rivera is inside the chart **2–5 minutes** before walking in.
- **Need:** Not “everything about the patient,” but **what changed or conflicts with today’s agenda** (new labs since last visit, pending imaging result, med changes by cardiology).
- **Why not a dashboard:** A dashboard optimizes for **comparability across widgets** (same tiles for every patient). This moment optimizes for **agenda-specific relevance** (“today is diabetes follow-up—surface glycemic and renal markers first”). Building that as fixed dashboard tiles becomes **brittle**—every clinic day mixes visit types.
- **Why not a sorted problem list / problem-oriented chart review:** Lists are **static ordering**; the physician’s *next* question depends on what they just read. The second question is rarely the second row on a list—it is **conditional** (“If creatinine is up, show me BP meds and last volume-related note”).
- **Why a conversational agent is the right solution:** **Follow-up without navigation churn.** The user steers retrieval through language (“only cardiology-relevant,” “ignore dermatology”) and can **repair** misunderstandings in one turn. Multi-turn is not cosmetic—it mirrors **clinical questioning**.

---

#### UC-02 — Medication reconciliation assist (interactive, not a printout)

- **Workflow anchor:** Mid-visit; reconciling home meds vs EHR active list after a hospitalization or specialist letter.
- **Need:** Identify **discrepancies** and **interaction risks** grounded in **current med list + problem list**—not generic drug-interaction spam unrelated to this patient.
- **Why not a dashboard:** Interaction dashboards usually show **pairwise drug classes** without tying to *this* patient’s renal function, adherence pattern, or who actually prescribed what.
- **Why not a sorted medication list:** The list answers “what’s ordered,” not “what should I ask the patient next?” The useful output is often a **question sequence** (“Was metformin stopped during admission intentionally?”).
- **Why a conversational agent:** Reconciliation is inherently **dialogic**—patient answers trigger new lookups. The agent can alternate **targeted retrieval** (meds/allergies/problems) with **clarifying prompts** the way a colleague would text—not the way a table sorts.

---

#### UC-03 — Lab trend explanation (“which result, which day, what changed?”)

- **Workflow anchor:** Physician sees an abnormal flag or conflicting numbers across facilities.
- **Need:** **Temporal** and **source** clarity—what lab, what reference range context, what changed since last draw.
- **Why not a sparkline gallery:** Sparklines answer **shape** but not **“why is this different from clinic last month?”** without reading around them.
- **Why not a single “labs” PDF-style report:** Reports are **frozen**; the next question is almost always **conditional** on the first answer.
- **Why a conversational agent:** The user picks the **dimension of drill-down** (time range, facility, analyte family) in **natural language**, which maps to **targeted Observation retrieval** + verification that numbers cited match FHIR rows.

---

#### UC-04 — Visit summary draft (grounded, iterative)

- **Workflow anchor:** End of visit; needs note-ready prose that still reflects **what was actually discussed** and **what is documented in chart facts**.
- **Need:** Shorten, then **re-tone** for billing vs clinical clarity; iterate after reading once.
- **Why not a template macro:** Templates **fight** mixed visit types and produce unsafe boilerplate (“reviewed all meds”) unless someone edits deeply—editing is multi-step.
- **Why not a dashboard:** Summarization is not a visualization problem; it is **language iteration under constraints**.
- **Why a conversational agent:** **Revision loops** (“shorter,” “add Medicare wellness language,” “remove anything not in vitals/labs we reviewed”) align with **multi-turn** generation + **verify** that claims remain tied to retrieved context.

---

#### UC-05 — Role-appropriate refusal (negative path, safety-critical)

- **Workflow anchor:** Session is valid but **role must not** receive clinical depth (e.g., nurse vitals-only workflow, admin scheduling-only workflow).
- **Need:** **Explicit refusal** naming role + blocked capability—not silent omission.
- **Why not a dashboard:** Dashboards **hide** denial by showing “what you’re allowed to see,” which confuses staff about **why** data are missing.
- **Why a conversational agent:** The agent can **state policy** and **suggest next step** (“ask the physician” / “open workflow in OpenEMR”) in the same turn—critical for **trust** and **training**.

---

#### UC-06 — Morning pass: “what changed overnight / since last visit **for today’s patients**”

- **Workflow anchor:** **8:50–9:00 AM**, between team huddle and first room—Dr. Rivera steps through **today’s schedule**, not in batch statistics but **patient-by-patient** in chart context.
- **Need:** For **each** upcoming encounter, a **fast risk scan**: new results, ED visits, consultant notes—**prioritized**, not raw feeds.
- **Why not a clinic-wide “incoming results” dashboard:** Those views **flood** equal-weight alerts; family medicine needs **visit-agenda filtering** (“this is a post-hospital follow-up—surface discharge Summary first”).
- **Why not only a sorted inbox:** Inbox sorts by **time**, not by **clinical relevance to today’s visit type**; the physician still must click everywhere.
- **Why a conversational agent (still chart-scoped):** For **each chart**, the user asks a **slightly different question** (“any new cancer staging?” vs “any insulin titration?”). A single static UI cannot hold that conditional logic without becoming **config hell**. Language is the **compression layer** for intent; tools retrieve **schedule + chart slices** per patient.

> **Architecture tie:** Multi-patient *morning* use is modeled as **sequential single-chart sessions** (OpenEMR chart context), not one mega-session across all patients—see session scoping in [`ARCHITECTURE.md`](ARCHITECTURE.md).

### 1.5 Who is *not* the v1 primary user (and why that matters)

| Persona | Why we defer | What would change if we chose them |
| --- | --- | --- |
| **ED resident, overnight intake** | Workflow is **parallel**, **high-acuity**, **interrupted**; tolerance for long answers is near zero; data sources skew to **external** and **incomplete**. | Sub-second UX targets, triage-oriented tools, different refusal semantics. |
| **Hospitalist with 12 admissions before noon** | Problem is **throughput** and **handoff**, not ambulatory chart priming. | Team census views, handoff notes, different RBAC mix. |

Naming these **excluded primaries** prevents “average clinician” slippage in architecture.

### 1.6 Traceability rule for implementation

Every agent capability in MVP should cite **at least one UC id** (UC-01…UC-06) in design notes or PR text. If it cannot be tied to a use case here, it should **not** ship as core product scope.

### 1.7 Relationship to `USER.md`

[`USER.md`](USER.md) holds a **short cross-reference** to this file. **Part 1 of `USERS.md` is authoritative** for Stage 4 / submission alignment.

### 1.8 Agent API authentication (how the copilot knows the role)

The FastAPI agent (`POST /agent/chat`) accepts **three** complementary paths—see [`PROJECT-SHOWCASE.md`](PROJECT-SHOWCASE.md) §1.3 for the full rationale:

1. **OpenEMR UI session (cookies)** — default for **embedded** chat: browser sends `Cookie` / `X-OpenEMR-Browser-Cookies`; the agent calls the PHP **session probe** (`/interface/copilot_session_probe.php`) to read group membership and map to `PHYSICIAN|NURSE|ADMIN`.
2. **Bearer token** — for **API / scripted** clients: `Authorization: Bearer …` validated via OpenEMR Standard API **`GET /apis/{site}/api/user`**.
3. **Demo bypass** — only when `AGENT_DEMO_BYPASS` is set: header `X-Agent-Demo-Role` trusts the role **without** OpenEMR (non-PHI demos).

**Clinician-facing scripted demos** (CSV cohort, tool summaries): [`deploy/CLINICIAN-WORKFLOWS.md`](deploy/CLINICIAN-WORKFLOWS.md).

---

## Part 2 — RBAC: Agent tool access (`rbac.py`)

This section matches **PRD v1.1 · Feature 8 (Role-Based Access Control)**.

**Normative source:** `AF/PRD.md` §4 Feature 8, §2 Definitions (`ADMIN`, `Role`).

---

### Important distinction: OpenEMR vs agent

- **Practice administrators** may have broad rights inside OpenEMR for scheduling, billing, and configuration. That is **out of MVP scope** for the co-pilot (PRD §3.4).
- For the **agent API**, the `ADMIN` OpenEMR role is intentionally **narrow**: if an admin session token calls the agent, the agent must **not** default to physician-level clinical access. That prevents **privilege escalation** through the co-pilot (PRD §2 Definitions, Feature 8).

---

### The eight patient-context tools

**Scaffold note:** The in-repo OpenAI tool surface exposes **five** read functions that map to this matrix: **demographics, medications, labs, vitals, allergies** ([`agent/tools/dispatch.py`](agent/tools/dispatch.py)). **Problem list, visit notes, and schedule** remain PRD-aligned targets for the OpenEMR fork—they are not yet registered as model-callable functions in this repository.

| # | Tool (logical name) | Purpose (summary) |
|---|---------------------|-------------------|
| 1 | `demographics` | Patient demographics |
| 2 | `problem_list` | Active problems / conditions |
| 3 | `medications` | Active medications |
| 4 | `labs` | Recent labs (`Observation`, `category=laboratory`) |
| 5 | `vitals` | Recent vitals (`Observation`, `category=vital-signs`) |
| 6 | `allergies` | Allergies and adverse reactions |
| 7 | `visit_notes` | Recent visit notes (clinical documentation) |
| 8 | `schedule` | Today’s visit / schedule context (REST) |

Labs and vitals are **separate tools** on the same FHIR resource type so RBAC can allow vitals without labs (PRD §3.3 NR-01 note, Feature 4).

---

### Permission matrix (agent)

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

**PRD acceptance (excerpt):** Nurse requests for **visit notes** or **labs** must return a **refusal** that names the **role** and the **blocked tool**—not silent filtering—and the refusal must be **logged** (Feature 8). **ADMIN** must receive refusal for any **clinical** tool (everything except `demographics` and `schedule`).

---

### Role flows (agent behavior)

#### PHYSICIAN

- All **eight** tools may run when the session is scoped to one patient and the token is valid.
- Answers must still pass verification (grounding + domain rules); RBAC does not bypass safety checks.

#### NURSE

- May use: `demographics`, `medications`, `vitals`, `allergies`, `schedule`.
- **Blocked:** `problem_list`, `labs`, `visit_notes` (and any composite flow that would pull equivalent data through another tool).
- **MVP agent scope:** tools are **read-only patient context** for grounding the model. Nursing documentation in OpenEMR itself is **not** defined as a separate “write notes” tool in Feature 8; do not imply write access in `rbac.py` unless the PRD is explicitly amended.

#### ADMIN (security boundary, not a co-pilot persona)

- May use: `demographics`, `schedule` **only**.
- All clinical tools must **refuse** with explanation + logging.

---

### Refusal behavior (required)

On deny:

1. Return a clear message: e.g. role **NURSE** cannot run tool **`labs`** (name both).
2. Log: role, tool, hashed identifiers per observability policy (PRD Feature 10).
3. Do not return partial clinical data from that tool via side channels.

---

### Decision flow (at a glance)

1. Resolve OpenEMR role: `PHYSICIAN` | `NURSE` | `ADMIN` (and unknown → deny).
2. For each tool the graph would call, check the matrix above.
3. If any tool is disallowed → **refuse** that tool (and aggregate message if multiple).

---

### `rbac.py`-style pseudo-code

```python
PHYSICIAN_TOOLS = frozenset({
    "demographics",
    "problem_list",
    "medications",
    "labs",
    "vitals",
    "allergies",
    "visit_notes",
    "schedule",
})
NURSE_TOOLS = frozenset({
    "demographics",
    "medications",
    "vitals",
    "allergies",
    "schedule",
})
ADMIN_TOOLS = frozenset({"demographics", "schedule"})


def allowed_tools(user_role: str):
    if user_role == "PHYSICIAN":
        return PHYSICIAN_TOOLS
    if user_role == "NURSE":
        return NURSE_TOOLS
    if user_role == "ADMIN":
        return ADMIN_TOOLS
    return frozenset()


def assert_tool_allowed(user_role: str, tool: str) -> None:
    if tool not in allowed_tools(user_role):
        raise ToolRefusal(
            f"Role {user_role} is not permitted to use tool {tool!r}."
        )
```

Implementations should map OpenEMR’s role strings to these three enums consistently with auth middleware (see `AF/architecture.md`, Tasks PR #12).
