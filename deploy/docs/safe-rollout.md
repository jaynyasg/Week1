# Safe rollout — agent, embedded chat UI, OpenEMR

Use this order when introducing or updating the Clinical Co-Pilot stack so you can **validate each hop** and **roll back** without guessing which layer failed.

## 1. Preconditions

| Check | Why it matters |
|--------|----------------|
| Fly apps exist and you are logged in (`fly auth whoami`) | Deploys and secrets target the right org. |
| Agent app can reach OpenEMR **public** URL | `OPENEMR_BASE_URL` on the agent must be the same origin users use in the browser (e.g. `https://clinical-copilot-v2.fly.dev`), not an internal-only hostname, because the agent calls `{OPENEMR_BASE_URL}/api/user` with forwarded cookies/tokens. |
| OpenEMR ↔ agent on Fly **6PN** | Embedded UI proxies `/agent` to `http://<agent-app>.internal:8080`. The OpenEMR image sets `CLINICAL_AGENT_INTERNAL_URL` (see root `fly.toml` `[env]`). |

## 2. Recommended deploy order

1. **Database (if applicable)** — MariaDB / volumes unchanged; no agent dependency.
2. **FastAPI agent** — `fly deploy --config fly.agent.toml`  
   - Set **`OPENEMR_BASE_URL`** to the **HTTPS** OpenEMR origin **before** relying on real sessions.  
   - Optional: **`OPENAI_API_KEY`**, **`AGENT_DEMO_BYPASS`** (non-production only), **`OPENAI_CHAT_MODEL`**.  
   - **`AGENT_CORS_ORIGINS`** only for a **separate-origin** SPA (e.g. standalone `clinical-chat-ui.fly.dev`). **Not** required for the UI embedded under OpenEMR (same origin).
3. **Smoke the agent** — `GET https://<agent>/agent/health` → `{"status":"ok"}`.  
4. **OpenEMR app** (when you are ready — replaces the running image) — `fly deploy --config fly.toml`  
   - Bakes **`/interface/copilot/`** and Apache **`/agent`** proxy (see `deploy/Dockerfile.fly` + `deploy/openemr_wrapper.sh`).  
5. **Verify embedded UI** — Log into OpenEMR, open **`/interface/copilot/`**, use **OpenEMR session** auth, send a test message.

## 3. Rollback

| Symptom | Action |
|---------|--------|
| Agent bad release | `fly releases --app <agent>` then `fly deploy --image <previous-image>` or rollback in the Fly dashboard. |
| OpenEMR bad release | Same pattern on the OpenEMR app; data on the **volume** is unchanged by a failed **new** deploy only if the old machines come back healthy—if the new image fails to start, fix forward or rollback the release. |
| Apache / proxy misconfig | `fly logs --app <openemr>`; `fly ssh console` and inspect generated `/etc/apache2/conf-enabled/99-clinical-copilot.conf` (path may vary). Temporarily rollback OpenEMR image if the app will not start. |

## 4. Correlation IDs

The agent:

- Accepts **`X-Request-ID`** (or `X-Correlation-ID` / `X-Trace-ID`).
- Echoes **`X-Request-ID`** on every response.
- Forwards it to OpenEMR on **`GET /api/user`** when validating the session.

Use the same ID in browser devtools, agent logs, and OpenEMR access logs when debugging auth failures.

## 5. Structured OpenEMR auth errors

When OpenEMR session validation fails, **`POST /agent/chat`** (and tool routes) may return **401** with JSON:

```json
{
  "detail": {
    "error": "openemr_auth_failed",
    "reason_code": "openemr_http_401",
    "message": "OpenEMR /api/user returned 401",
    "request_id": "…"
  }
}
```

Logs include **`event_type=openemr_auth_failure`** with the same **`reason_code`** and **`client_request_id`**.

## 6. Tunables (non-secret)

| Variable | App | Purpose |
|----------|-----|---------|
| `OPENEMR_HTTP_TIMEOUT_SECONDS` | Agent | Timeout for outbound `/api/user` and shared `httpx` client (default `30`). |
| `AGENT_MAX_BODY_BYTES` | Agent | Max `Content-Length` for POST/PUT/PATCH (default `262144`; floor `64`). |
| `AGENT_RATE_LIMIT_CHAT` | Agent | Optional SlowAPI limit for **`POST /agent/chat`** only (e.g. `60/minute`). Unset = no limit. |
| `CLINICAL_AGENT_INTERNAL_URL` | OpenEMR | Upstream for Apache `ProxyPass /agent` (default `http://clinical-agent-scaffold.internal:8080`). |

## 7. Further reading

- [operator-runbook.md](operator-runbook.md) — symptom → checks.
- [preview-environment.md](preview-environment.md) — separate Fly apps for safe iteration.
- [architecture-embedded-proxy.md](architecture-embedded-proxy.md) — browser → Apache → agent flow.

## 8. What **not** to mix on production PHI

- **`AGENT_DEMO_BYPASS=1`** with **`X-Agent-Demo-Role`** skips real OpenEMR validation — acceptable only for throwaway demos.
