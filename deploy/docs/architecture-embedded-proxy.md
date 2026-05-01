# Architecture note — embedded chat UI + `/agent` reverse proxy

## Request path (browser → agent)

1. User opens **`https://<openemr-host>/interface/copilot/`** (static SPA baked into the OpenEMR image).
2. SPA calls **`POST /agent/chat`** on the **same host** (relative URL).
3. Apache on the OpenEMR container matches **`ProxyPass /agent`** and forwards to **`CLINICAL_AGENT_INTERNAL_URL`** (Fly 6PN), e.g. `http://clinical-agent-scaffold.internal:8080/agent/chat`.
4. FastAPI agent validates session via **`OPENEMR_BASE_URL/api/user`**, forwarding **`Authorization`** and/or **`Cookie`** from the original browser request (proxy preserves headers when configured).

## Why same-origin matters

OpenEMR session cookies are scoped to the OpenEMR **site origin**. A standalone SPA on another hostname cannot send those cookies to the agent unless you paste headers or use OAuth. Embedding under **`/interface/copilot/`** keeps the browser on one origin so **`credentials: 'include'`** works with the proxy.

## Files

| Piece | Location |
|-------|-----------|
| Vite build + `base` path | `chat-ui/`, `VITE_BASE_PATH=/interface/copilot/` in `deploy/Dockerfile.fly` |
| Apache fragment (runtime) | Written by `deploy/openemr_wrapper.sh` → `99-clinical-copilot.conf` |
| Agent upstream | `fly.toml` `[env] CLINICAL_AGENT_INTERNAL_URL` |

## Caveats

- **`mod_proxy`** must be enabled in the OpenEMR base image (`deploy/enable-apache-proxy-modules.sh`).
- **`OPENEMR_BASE_URL`** on the agent must still be the **public** HTTPS OpenEMR URL so `/api/user` matches cookie scope.
- **CORS** on the agent is irrelevant for this path (same origin to OpenEMR); still needed for a separate-origin SPA.
