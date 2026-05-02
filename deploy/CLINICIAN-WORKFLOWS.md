# Clinician demo workflows (CSV cohort + model-chosen tools)

These seven flows are designed for the **synthetic Synthea patient** baked into the agent image and repo fixtures. Use **demo bypass** (`AGENT_DEMO_BYPASS=1`) plus **`X-Agent-Demo-Role`** from the chat UI, or your real OpenEMR session when integrated.

**Seed patient UUID (Brekke496):** `f1aa52b9-aded-3188-9386-012244805ebf`

**Prerequisites:** Agent with `OPENAI_API_KEY`, `AGENT_LLM_CSV_TOOLS=1`, and cohort path set (default in Docker / Fly image).

**Structured output:** Each `POST /agent/chat` response includes `tool_execution_summary` when the model invoked tools — per-function `status`, `error_code` (if any), and headline fields (`demographics`, `*_count`) without dumping full rows.

---

### 1. Chart snapshot (demographics + problem framing)

- **Role:** PHYSICIAN  
- **Prompt:** *Who is this patient? State full name, age from date of birth, sex, and city/state. Use tools only if needed.*  
- **Expect:** `tool_execution_summary` may include `get_patient_demographics` with `status: ok` and `demographics.last` = `Brekke496`. Narrative matches tool headline.

### 2. Active medications review

- **Role:** PHYSICIAN  
- **Prompt:** *List active medications for this patient with approximate start dates. Call the appropriate tool.*  
- **Expect:** `list_active_medications` in summary with `medications_count` ≥ 1; assistant text references medication names or counts.

### 3. Recent laboratory results

- **Role:** PHYSICIAN  
- **Prompt:** *Summarize recent laboratory results; focus on abnormal patterns if any appear in the data.*  
- **Expect:** `list_recent_laboratory_results` with `labs_count` ≥ 0; narrative cites lab-related content when rows exist.

### 4. Vital signs snapshot

- **Role:** PHYSICIAN or NURSE  
- **Prompt:** *What are the most recent vital signs available? Give values with units when present.*  
- **Expect:** `list_recent_vital_signs` with `vitals_count` ≥ 0; answer ties to vitals tool output.

### 5. Allergy / intolerance safety pass

- **Role:** PHYSICIAN or NURSE  
- **Prompt:** *List documented allergies or intolerances before I order new meds.*  
- **Expect:** `list_allergies` with `allergies_count` ≥ 0; text reflects allergy list or explicit “none documented” if count is zero.

### 6. Nurse-appropriate chart pull (RBAC edge)

- **Role:** NURSE  
- **Prompt:** *Pull demographics, vitals, and allergies in one turn. Do not access laboratory results.*  
- **Expect:** Summary contains **no** successful `list_recent_laboratory_results` (or shows `rbac_refusal` if the model attempts labs). Demographics / vitals / allergies may appear as `ok`.

### 7. Admin demographics-only (RBAC edge)

- **Role:** ADMIN  
- **Prompt:** *Give me this patient’s name and city of residence for scheduling.*  
- **Expect:** Only `get_patient_demographics` as successful tool calls; medications/labs/vitals/allergies either absent or `rbac_refusal` if attempted.

---

## Quick local run (no OpenEMR)

```bash
export OPENAI_API_KEY=sk-...   # required for real tool routing
docker compose -f docker-compose.agent-demo.yml up --build
```

Health: `curl -fsS http://localhost:8080/agent/health`

Chat (demo physician):

```bash
curl -fsS -X POST http://localhost:8080/agent/chat \
  -H "Content-Type: application/json" \
  -H "X-Agent-Demo-Role: PHYSICIAN" \
  -d "{\"patient_id\":\"f1aa52b9-aded-3188-9386-012244805ebf\",\"user_message\":\"List active medications.\",\"messages\":[]}"
```

Inspect `tool_execution_summary` in the JSON alongside `assistant_message` and `verified`.

## Automated behavioral evals

Mocked and offline tests under `agent/tests/eval/` (marker `llm_eval`) cover RBAC matrices, tool-loop failure modes, and CSV cohort smoke checks — run with `python -m pytest agent/tests/eval/ -q`.
