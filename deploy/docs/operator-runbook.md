# Operator runbook — agent + embedded UI

Quick triage when something looks wrong. All commands assume Fly CLI and access to app logs.

## Symptom → checks

### 1. Agent returns 502 / connection errors

1. `fly status --app <agent-app>`
2. `fly logs --app <agent-app>` (look for crash loops, OOM)
3. Confirm **`internal_port`** matches Uvicorn listen port (8080) in `fly.agent.toml` and `Dockerfile.agent`.

### 2. `POST /agent/chat` always 401

1. Confirm **`OPENEMR_BASE_URL`** is set to the **public** OpenEMR HTTPS origin (same host users log into).
2. For embedded UI: browser must send cookies — user must be logged into OpenEMR on that origin; Apache proxy must forward `/agent` (see `deploy/openemr_wrapper.sh`).
3. For demo: **`AGENT_DEMO_BYPASS=1`** and **`X-Agent-Demo-Role`** (not for PHI).
4. Correlate with **`X-Request-ID`**: agent echoes it; OpenEMR `/api/user` receives the same header when configured.

### 3. `413 payload_too_large`

- Reduce request size or raise **`AGENT_MAX_BODY_BYTES`** (floor 64 in code).

### 4. `429` from agent

- **`AGENT_RATE_LIMIT_CHAT`** is set (e.g. `60/minute`). Increase limit or unset for dev.

### 5. OpenEMR UI `/interface/copilot/` 404 or blank

1. Confirm deploy used **`deploy/Dockerfile.fly`** (multi-stage with Vite build).
2. `fly ssh console --app <openemr-app>` — verify `/var/www/localhost/htdocs/openemr/interface/copilot/index.html` exists.
3. Check Apache includes **`99-clinical-copilot.conf`** (path may be `conf-enabled` or `conf.d`).

### 6. CORS errors in browser (standalone SPA only)

- Set **`AGENT_CORS_ORIGINS`** on the agent to the SPA origin. Embedded OpenEMR UI is same-origin — CORS not required for `/agent` via proxy.

## Useful endpoints

| Path | Purpose |
|------|---------|
| `GET /agent/health` | Liveness |
| `GET /agent/health/ready` | Config snapshot (`openemr_base_url_configured`) |
| `GET /agent/metrics` | Prometheus stub (`clinical_agent_up`) |

Optional smoke: `scripts/smoke_agent_optional.ps1` / `.sh` (see repo `Makefile` `smoke-help`).
