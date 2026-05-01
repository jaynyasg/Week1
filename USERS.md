# RBAC — Agent tool access (`rbac.py`)

For **primary-user persona and clinical use-case traceability** (Gauntlet `USER.md`), see [`USER.md`](USER.md).

This document matches **PRD v1.1 · Feature 8 (Role-Based Access Control)**. Enforcement happens at the **agent layer** (e.g. retrieve node → `rbac.py`) so role boundaries are not UI-only.

**Normative source:** `AF/PRD.md` §4 Feature 8, §2 Definitions (`ADMIN`, `Role`).

---

## Important distinction: OpenEMR vs agent

- **Practice administrators** may have broad rights inside OpenEMR for scheduling, billing, and configuration. That is **out of MVP scope** for the co-pilot (PRD §3.4).
- For the **agent API**, the `ADMIN` OpenEMR role is intentionally **narrow**: if an admin session token calls the agent, the agent must **not** default to physician-level clinical access. That prevents **privilege escalation** through the co-pilot (PRD §2 Definitions, Feature 8).

---

## The eight patient-context tools

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

## Permission matrix (agent)

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

## Role flows (agent behavior)

### PHYSICIAN

- All **eight** tools may run when the session is scoped to one patient and the token is valid.
- Answers must still pass verification (grounding + domain rules); RBAC does not bypass safety checks.

### NURSE

- May use: `demographics`, `medications`, `vitals`, `allergies`, `schedule`.
- **Blocked:** `problem_list`, `labs`, `visit_notes` (and any composite flow that would pull equivalent data through another tool).
- **MVP agent scope:** tools are **read-only patient context** for grounding the model. Nursing documentation in OpenEMR itself is **not** defined as a separate “write notes” tool in Feature 8; do not imply write access in `rbac.py` unless the PRD is explicitly amended.

### ADMIN (security boundary, not a co-pilot persona)

- May use: `demographics`, `schedule` **only**.
- All clinical tools must **refuse** with explanation + logging.

---

## Refusal behavior (required)

On deny:

1. Return a clear message: e.g. role **NURSE** cannot run tool **`labs`** (name both).
2. Log: role, tool, hashed identifiers per observability policy (PRD Feature 10).
3. Do not return partial clinical data from that tool via side channels.

---

## Decision flow (at a glance)

1. Resolve OpenEMR role: `PHYSICIAN` | `NURSE` | `ADMIN` (and unknown → deny).
2. For each tool the graph would call, check the matrix above.
3. If any tool is disallowed → **refuse** that tool (and aggregate message if multiple).

---

## `rbac.py`-style pseudo-code

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
