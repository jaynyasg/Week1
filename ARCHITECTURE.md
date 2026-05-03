# Clinical Co-Pilot — System Architecture

**AgentForge · Gauntlet AI**

## Executive summary (~500 words)

**User and use-case constraints** (who it is for, workflow moments, and why an agent—not a dashboard—per UC) are defined in [`USERS.md`](USERS.md) Part 1; this architecture **must trace** to that document.

The Clinical Co-Pilot is a **chart-scoped conversational agent** that sits beside OpenEMR: clinicians authenticate with **trust the EHR already holds**:

- **Browser / embedded UI:** `Cookie` (and optionally `X-OpenEMR-Browser-Cookies`) forwarded to **`GET {origin}/interface/copilot_session_probe.php`**, which validates the PHP session and returns JSON used to map **`PHYSICIAN` / `NURSE` / `ADMIN`**.
- **API / automation:** `Authorization: Bearer …` validated against OpenEMR **Standard API** **`GET /apis/{site_id}/api/user`** (not a generic `/api/user` on the site root).
- **Demo only:** `AGENT_DEMO_BYPASS=1` plus **`X-Agent-Demo-Role`** skips OpenEMR for throwaway demos—**never** with real PHI.

The agent never replaces OpenEMR authorization; it **inherits** session semantics and enforces an additional **tool-level RBAC** matrix (`PHYSICIAN`, `NURSE`, `ADMIN`, etc.) so that retrieval paths cannot escalate privileges (see [`USERS.md`](USERS.md)).

At runtime the assistant follows a **retrieve → generate → verify** loop. **Retrieve** uses **model-chosen tools** in the shipped scaffold: five OpenAI functions (**demographics, medications, laboratory observations, vital-sign observations, allergies**) backed by **Synthea-style CSV fixtures** and/or **live OpenEMR FHIR R4** when credentials are configured (`agent/tools/dispatch.py`, `agent/tools/openemr_fhir.py`). **Eight** distinct PRD logical tools (including **problem list**, **visit notes**, **schedule**) remain the **target** surface—see [`USERS.md`](USERS.md) Part 2 and the mermaid diagram below.

**Trust boundaries** are explicit: (1) OpenEMR session boundary, (2) RBAC enforcement before side-effecting or sensitive retrieval, (3) verification before user-visible assertions as facts, (4) logging that must not leak raw tokens or full PHI. The **HTTP API** exposes `POST /agent/chat` with multi-turn `messages` and session correlation via **`X-Clinical-Session-Id`**. Responses include **`assistant_message`**, verification metadata (`verified`, `verify_retry_count`, `verification_notes`), and **tool result keys** for traceability. Observability is **not optional**: structured **`agent_event`** log lines (see `agent/observability/`) record turn completion, category-boundary review signals, and RBAC refusals; future phases wire deeper cost/token export. **Deployment** uses a **separate Fly.io app** for the agent (`fly.agent.toml`, `Dockerfile.agent`) so the OpenEMR stack and agent can scale and roll independently. The **chat UI** is a **Vite + React** SPA, embedded from the OpenEMR image at `/interface/copilot/` with Apache proxying `/agent` and `/interface/clinical-agent` to the agent service (see [`deploy/Dockerfile.fly`](deploy/Dockerfile.fly), [`deploy/openemr_wrapper.sh`](deploy/openemr_wrapper.sh)).

**Known tradeoffs in this repo snapshot:** the **mermaid** diagram and table below describe the **target** architecture (LangGraph, Langfuse, `POST /flag`); the **checked-in code** proves **contracts, ordering, session + Bearer + demo auth paths, and testable verification fields** on a **FastAPI + OpenAI tool-calling scaffold**. Full **record-level source attribution in prose**, **production-only LLM** hardening, and **all eight PRD tools** are tracked in [`.planning/ROADMAP.md`](.planning/ROADMAP.md) and [`USERS.md`](USERS.md) as **fork / deployment** work. **Behavioral eval inventory:** [`EVAL.md`](EVAL.md) (53 core + 21 edge-case tests under `agent/tests/eval/`).

---

## Diagram and component view

This diagram shows the full system architecture for the Clinical Co-Pilot, including the browser client, cloud infrastructure (OpenEMR + Agent microservice), external LLM, and test infrastructure. Reflects PRD v1.1: 8 tools (vitals split from labs), POST /flag endpoint, session scoping, and agent-unreachable fallback state.

```mermaid
flowchart TB
    classDef browser  fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F
    classDef openemr  fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef agent    fill:#EDE9FE,stroke:#7C3AED,color:#3B0764
    classDef verify   fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    classDef external fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef db       fill:#F1F5F9,stroke:#64748B,color:#1E293B
    classDef obs      fill:#CCFBF1,stroke:#0D9488,color:#134E4A
    classDef test     fill:#FFE4E6,stroke:#BE123C,color:#881337
    classDef infra    fill:#F8FAFC,stroke:#94A3B8,color:#334155

    subgraph BROWSER["🖥️  Physician Browser"]
        OPAGE["OpenEMR Chart Page"]
        CHATJS["Chat Panel\nchat.js · stream.js · ui.js"]
        OPAGE --> CHATJS
    end

    subgraph CLOUD["☁️  Docker Compose — Railway / Fly.io"]

        NGX["⚙️ Nginx\nReverse Proxy · SSL Termination"]

        subgraph OPENEMR_C["📋  OpenEMR — PHP / Apache"]
            PHP_APP["PHP Application\nChart · Auth · Modules"]
            COPILOT["copilot_panel.php\nconfig.php"]
            FHIR_EP["FHIR R4 API\n/apis/default/fhir/"]
            REST_EP["REST API\n/api/appointment · /api/user"]
        end

        subgraph DB_C["🗄️  MySQL"]
            DB[("Patient Database\nPHI · EHR Records")]
        end

        subgraph AGENT_C["🤖  Agent Microservice — FastAPI · Python 3.11"]

            subgraph API_L["API Layer"]
                ROUTES["POST /chat · POST /summary\nPOST /flag\nGET /chat/stream SSE"]
                AUTH_MW["Auth Middleware\nToken Validation · Role Injection"]
                LOG_MW["PHI-Safe Logger\nSHA-256 Hashed IDs · JSON"]
            end

            AGENT_STATE["AgentState\npatient_id · user_role · session_id\nmessages · tool_results · verified"]

            subgraph GRAPH_L["LangGraph State Machine"]
                RETRIEVE_N["Retrieve Node\nTool Dispatch"]
                GENERATE_N["Generate Node\nPrompt Assembly · LLM Call"]
                VERIFY_N["Verify Node\nGrounding + Domain Rules"]
            end

            subgraph VERIF_L["Verification Layer"]
                GROUND["grounding.py\nSource Attribution Check"]
                DOMAIN["domain_rules.py\nAllergy · Lab Range · Date Logic"]
            end

            subgraph TOOLS_L["Patient Context Tools  (8 total)"]
                FHIR_TOOLS["FHIR Tools ×7\ndemographics · medications\nlabs · vitals · allergies\nproblem_list · visit_notes"]
                REST_TOOLS["schedule.py\nREST Tool"]
            end

            subgraph EHR_L["EHR Data Clients"]
                FHIR_CL["fhir_client.py\nAsync FHIR R4 Client"]
                REST_CL["openemr_client.py\nREST API Client"]
            end

            RBAC["rbac.py\nPHYSICIAN · NURSE · ADMIN\nPermission Matrix"]
        end

        subgraph LFUSE["📊  Langfuse — Self-Hosted"]
            LF["Observability Dashboard\nTraces · Spans · Token Costs · Latency"]
        end

    end

    subgraph EXT["🌐  External Services"]
        CLAUDE["Anthropic API\nClaude Sonnet\nToken Streaming"]
    end

    subgraph TESTS["🧪  Test Infrastructure"]
        UNIT_T["Unit Tests\nagent/tests/unit/  ·  9 files\nNo live services required"]
        INTG_T["Integration Tests\nagent/tests/integration/  ·  4 files\nRequires running OpenEMR"]
        EVAL_T["Eval Suite\nagent/eval/  ·  20+ cases\nHappy path · Missing data\nAuth boundary · Adversarial"]
    end

    %% ── Browser ↔ Nginx ──────────────────────────────────────────────────
    CHATJS -->|"HTTPS  ·  SSE"| NGX
    NGX    -->|"SSE token stream"| CHATJS

    %% ── Nginx routing ────────────────────────────────────────────────────
    NGX -->|"/ → OpenEMR :80"| PHP_APP
    NGX -->|"/agent → FastAPI :8000"| ROUTES
    PHP_APP --> COPILOT
    COPILOT -.->|"injects widget into chart"| CHATJS

    %% ── OpenEMR internals ────────────────────────────────────────────────
    PHP_APP --> FHIR_EP & REST_EP
    FHIR_EP & REST_EP --> DB

    %% ── Auth: agent validates OpenEMR session token ───────────────────────
    AUTH_MW -->|"GET /api/user — validate session"| REST_EP

    %% ── API layer flow ───────────────────────────────────────────────────
    ROUTES --> AUTH_MW & LOG_MW
    ROUTES --> AGENT_STATE
    AGENT_STATE --> RETRIEVE_N

    %% ── LangGraph node flow ───────────────────────────────────────────────
    RETRIEVE_N --> GENERATE_N --> VERIFY_N
    VERIFY_N   -->|"verified: false  ·  retry ≤ 1"| GENERATE_N
    VERIFY_N   -->|"verified: true"| ROUTES

    %% ── RBAC ─────────────────────────────────────────────────────────────
    RETRIEVE_N -->|"enforce(role, tool)"| RBAC

    %% ── Tools → EHR clients → OpenEMR APIs ──────────────────────────────
    RETRIEVE_N  --> FHIR_TOOLS & REST_TOOLS
    FHIR_TOOLS  --> FHIR_CL
    REST_TOOLS  --> REST_CL
    FHIR_CL     -->|"FHIR R4 queries"| FHIR_EP
    REST_CL     -->|"REST calls"| REST_EP

    %% ── LLM call ─────────────────────────────────────────────────────────
    GENERATE_N -->|"prompt + tool_results"| CLAUDE
    CLAUDE     -->|"token stream"| GENERATE_N

    %% ── Verification internals ───────────────────────────────────────────
    VERIFY_N --> GROUND & DOMAIN

    %% ── Observability ────────────────────────────────────────────────────
    RETRIEVE_N & GENERATE_N & VERIFY_N -->|"spans"| LF
    LOG_MW -->|"request logs"| LF
    ROUTES -->|"FLAG events  ·  turn_index · reason"| LF

    %% ── Test targets ─────────────────────────────────────────────────────
    UNIT_T -.->|"mocks + asserts"| AGENT_C
    INTG_T -.->|"live calls"| AGENT_C
    INTG_T -.->|"live calls"| OPENEMR_C
    EVAL_T -.->|"end-to-end"| AGENT_C

    %% ── Class assignments ────────────────────────────────────────────────
    class OPAGE,CHATJS browser
    class PHP_APP,COPILOT,FHIR_EP,REST_EP openemr
    class ROUTES,AUTH_MW,LOG_MW,AGENT_STATE,RETRIEVE_N,GENERATE_N,FHIR_TOOLS,REST_TOOLS,FHIR_CL,REST_CL,RBAC agent
    class GROUND,DOMAIN,VERIFY_N verify
    class CLAUDE external
    class DB db
    class LF obs
    class UNIT_T,INTG_T,EVAL_T test
    class NGX infra
```

---

## Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent placement | Separate FastAPI microservice in same Docker network | Keeps Python/AI code cleanly separated from OpenEMR PHP; communicates via FHIR/REST API |
| Data access | FHIR R4 as primary, direct MySQL as fallback | FHIR is the standard; some resources (e.g. appointments) require REST fallback |
| Auth flow | OpenEMR **session probe** (cookies) and/or **Bearer** to Standard API `/apis/{site}/api/user`; optional **demo bypass** for non-PHI demos | No parallel login; automation and embedded UI covered; demo isolated by env |
| LLM | Claude Sonnet (Anthropic) | Large context window, reliable JSON output, best instruction following for clinical structured output |
| Agent framework | LangGraph | Explicit state management for multi-turn sessions; retrieve → generate → verify loop with retry |
| Verification | Programmatic grounding check + domain rules | Faster than LLM-as-judge; deterministic; catches hallucinations and clinical constraint violations |
| Observability | Langfuse (self-hosted) | HIPAA-compatible; full trace visibility across all LangGraph nodes |
| Frontend | **React + TypeScript + Vite** chat UI embedded under OpenEMR `/interface/copilot/` (standalone Fly app optional) | Typed client, `VITE_*` build args; Apache `ProxyPass` to FastAPI for same-origin cookies |
| Vitals / labs split | Two OpenAI tools on FHIR `Observation` (`category=laboratory` vs `vital-signs`) | NURSE can access vitals without labs; RBAC boundary matches PRD |
| Session scoping | `AgentState` is bound to one `patient_id`; navigation change resets state | Prevents context bleed between patients; aligns with clinical workflow of one chart at a time |
| Incorrect response flagging | `POST /flag` writes a `FLAG` event to Langfuse; no re-generation | Audit trail for clinical safety; out-of-scope to auto-correct responses in v1 |
| Graceful degradation | Frontend renders static "Co-Pilot unavailable" banner when agent service is unreachable | Clinicians can still use OpenEMR normally; agent failure must not block core EHR workflows |
