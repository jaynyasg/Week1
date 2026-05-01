# Fly.io — FastAPI agent scaffold (`agent.http.app:create_app`)

This runbook deploys **only** the Python agent service (Uvicorn + FastAPI). It does **not** replace the OpenEMR + MariaDB stack documented in [deployment.md](docs/deployment.md) and the OpenEMR app config in the repository root `fly.toml`.

The agent listens on **8080** inside the container. Fly maps public HTTPS to that port via `http_service.internal_port` in `fly.agent.toml`.

## Preflight checklist

Before `fly deploy`, confirm each item:

| Step | What to verify |
|------|----------------|
| **flyctl** | [`flyctl` is installed](https://fly.io/docs/hands-on/install-flyctl/) and on your `PATH` (`fly version`). |
| **Auth** | Run `fly auth login`, then `fly auth whoami` — you must see the intended account/org. |
| **App name** | The `app = "..."` value in `fly.agent.toml` must be **globally unique** on Fly.io. If `fly apps create <name>` fails, pick another name and pass `--app <name>` on deploy or update `fly.agent.toml`. |
| **`OPENEMR_BASE_URL` secret** | Required for `/agent/chat` (and tool routes that call OpenEMR) unless you rely solely on **demo bypass** (see below). Set before relying on chat: `fly secrets set OPENEMR_BASE_URL=https://your-openemr-host.example.com --app <your-app>`. **`/agent/health` does not need this secret.** |
| **`OPENAI_API_KEY` secret** | When set, `POST /agent/chat` uses **OpenAI** (`gpt-4o-mini` by default; override with `OPENAI_CHAT_MODEL`) for the generate step instead of the offline echo scaffold. Omit in CI or local dev if you want echo-only behavior. |
| **`AGENT_CORS_ORIGINS`** | Optional comma-separated list of browser origins allowed to call the API (e.g. `https://clinical-chat-ui.fly.dev`). Use `*` only for throwaway demos (no credentials). Unset = no CORS middleware. |
| **OCI source label (`IMAGE_SOURCE_URL`)** | `Dockerfile.agent` sets `org.opencontainers.image.source` from build-arg **`IMAGE_SOURCE_URL`**. Defaults live in **`fly.agent.toml`** under **`[build.args]`** (placeholder `https://gitlab.com/CHANGE_ME/Week1` — replace **`CHANGE_ME`**). Override without editing the file: `fly deploy --config fly.agent.toml --build-arg IMAGE_SOURCE_URL=https://gitlab.com/your-group/Week1`. |

**Org:** If you belong to multiple orgs, use `--org <slug>` on `fly apps create` / deploy or set the org in the Fly dashboard. Personal accounts default to your user org.

**Never commit secrets.** Use `fly secrets set` only; values live in Fly’s secret store, not in git.

## Port alignment (8080)

Keep these three in sync or you will see wrong-host / connection errors behind the proxy:

| Location | Value |
|----------|--------|
| `Dockerfile.agent` | `EXPOSE 8080`, Uvicorn `--port 8080`, healthcheck `http://127.0.0.1:8080/...` |
| `fly.agent.toml` | `[env] PORT = "8080"`, `[http_service] internal_port = 8080` |

If you change the container listen port, update **both** the Dockerfile and `internal_port` (and `PORT`) together.

## One-time: login

```bash
fly auth login
fly auth whoami
```

## Create the app and deploy

Pick a **globally unique** app name (change `app` in `fly.agent.toml` or use `--app` on every command).

### Option A — `fly launch` (interactive)

From the **repository root**, you can run `fly launch` and point it at this repo’s Dockerfile when prompted, **or** copy `fly.agent.toml` to a scratch directory and merge the generated file — `fly launch` often expects a single `fly.toml`. The most predictable path for this repo is Option B.

### Option B — `fly apps create` + deploy (recommended)

```bash
cd /path/to/Week1
fly apps create clinical-agent-scaffold
fly secrets set OPENEMR_BASE_URL=https://your-openemr.fly.dev --app clinical-agent-scaffold
fly deploy --config fly.agent.toml --app clinical-agent-scaffold \
  --build-arg IMAGE_SOURCE_URL=https://gitlab.com/your-group/Week1
```

Ensure `fly.agent.toml` has the same `app = "clinical-agent-scaffold"` or always pass `--app`. Omit **`--build-arg`** if you already set **`[build.args].IMAGE_SOURCE_URL`** in **`fly.agent.toml`** to your canonical HTTPS git URL.

### OCI image source

Build-arg **`IMAGE_SOURCE_URL`** (see **`fly.agent.toml`** **`[build.args]`** and **`Dockerfile.agent`**):

- **`fly.agent.toml`** declares **`[build.args].IMAGE_SOURCE_URL`** so remote builds embed **`org.opencontainers.image.source`** in the image (see **`Dockerfile.agent`**).
- **CLI override:** `fly deploy --config fly.agent.toml --build-arg IMAGE_SOURCE_URL=https://your-host/owner/repo` wins over the TOML default for that deploy.
- **GitHub Actions:** [`.github/workflows/fly-agent-manual.yml`](../.github/workflows/fly-agent-manual.yml) passes **`--build-arg IMAGE_SOURCE_URL=https://github.com/${{ github.repository }}`** so mirrors on GitHub get a correct **`github.com/owner/repo`** label. If **GitLab** (or another host) is canonical, change **`[build.args]`** in **`fly.agent.toml`** or deploy from the CLI with **`--build-arg`** as above.

## GitHub Actions

A manual deploy workflow lives at [`.github/workflows/fly-agent-manual.yml`](../.github/workflows/fly-agent-manual.yml). It is triggered only by [`workflow_dispatch`](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch) (GitHub **Actions** → **Fly agent (manual deploy)** → **Run workflow**).

Add a repository secret named **`FLY_API_TOKEN`** (repository **Settings** → **Secrets and variables** → **Actions**). Create a deploy-scoped token with Fly’s CLI or dashboard; see Fly’s **[Access tokens / deploy tokens](https://fly.io/docs/reference/deploy-tokens/)** and the [`fly tokens create deploy`](https://fly.io/docs/flyctl/tokens-create-deploy/) reference. Do not commit token values or paste them into the workflow file.

The workflow uses **`concurrency`** with a single group so overlapping manual runs **queue** instead of canceling each other (`cancel-in-progress: false`), which avoids interrupting an in-flight deploy when another run is started.

The workflow pins **`superfly/flyctl-actions/setup-flyctl@1.5`** (not a moving `@master` ref) and includes a **fail-fast** step if the **`FLY_API_TOKEN`** secret is missing, so the job errors immediately instead of running `flyctl` with an empty token.

On deploy it adds **`--build-arg IMAGE_SOURCE_URL=https://github.com/${{ github.repository }}`** so the image OCI label points at this GitHub repo. Repos whose **canonical** remote is GitLab (or elsewhere) should rely on **`[build.args]`** in **`fly.agent.toml`** or a manual **`fly deploy --build-arg IMAGE_SOURCE_URL=...`** instead (see [OCI image source](#oci-image-source)).

## Secrets

```bash
fly secrets set OPENEMR_BASE_URL=https://your-openemr-host.example.com --app clinical-agent-scaffold
fly secrets set OPENAI_API_KEY=sk-... --app clinical-agent-scaffold
# Optional: allow the static chat UI origin to call the API from the browser
fly secrets set AGENT_CORS_ORIGINS=https://clinical-chat-ui.fly.dev --app clinical-agent-scaffold
```

- No trailing slash required (the app normalizes it).
- Do **not** put OpenEMR cookies or bearer tokens in Fly secrets for generic chat; clients send `Authorization` per request. Only set additional secrets if you add features that need them.

## Static chat UI (optional second Fly app)

The repo includes **`chat-ui/`**: a Vite + React SPA (message history, role switcher, demo vs bearer auth, error states). Deploy it as its **own** Fly app so the agent API URL is baked at image build time. Run deploy **from the `chat-ui/` directory** so the Docker build context matches `Dockerfile` + `fly.toml`:

```bash
cd chat-ui
fly apps create clinical-chat-ui   # name must be globally unique; edit fly.toml if needed
fly deploy --build-arg VITE_AGENT_BASE_URL=https://clinical-agent-scaffold.fly.dev
```

Set **`AGENT_CORS_ORIGINS`** on the **agent** app to the chat UI’s public origin (see Secrets). For local dev, run Uvicorn on `127.0.0.1:8080` and `npm run dev` in `chat-ui/` (Vite proxies `/agent` to `VITE_DEV_PROXY_TARGET`, default `http://127.0.0.1:8080`).

## Smoke checks

### curl (from any shell)

Replace the hostname with your app name:

```bash
curl -fsS https://clinical-agent-scaffold.fly.dev/agent/health
# Expect JSON: {"status":"ok"}
```

**Optional** — `POST /agent/chat` against a **real** OpenEMR session. The agent accepts **either** an `Authorization` header **or** a `Cookie` header (or both) and forwards them to `{OPENEMR_BASE_URL}/api/user` to validate the session and resolve an RBAC role. At least one of the two must be present and non-blank, otherwise the request is rejected with **`401 Missing Authorization or Cookie header`**.

OAuth2 / Bearer (copy `Authorization` from your browser’s network tab while logged into OpenEMR, same as local dev):

```bash
curl -fsS -X POST "https://clinical-agent-scaffold.fly.dev/agent/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <paste-from-browser-openemr-request>" \
  -d "{\"patient_id\":\"1\",\"messages\":[],\"user_message\":\"Hello\"}"
```

Cookie-based session (when your OpenEMR install only authenticates the UI with PHP session cookies — e.g. `OpenEMR=...; PHPSESSID=...; token_main=...`). Open DevTools → **Network** on a page in your logged-in OpenEMR, pick any request to your OpenEMR origin, and copy the **entire** `Cookie:` request header value into the curl below:

```bash
curl -fsS -X POST "https://clinical-agent-scaffold.fly.dev/agent/chat" \
  -H "Content-Type: application/json" \
  -H "Cookie: <paste-full-cookie-string-from-logged-in-openemr-request>" \
  -d "{\"patient_id\":\"1\",\"messages\":[],\"user_message\":\"Hello\"}"
```

PowerShell variant (note the escaped quotes in `-d` and the single-line `-H "Cookie: ..."`):

```powershell
curl.exe -fsS -X POST "https://clinical-agent-scaffold.fly.dev/agent/chat" `
  -H "Content-Type: application/json" `
  -H "Cookie: <paste-full-cookie-string-from-logged-in-openemr-request>" `
  -d '{\"patient_id\":\"1\",\"messages\":[],\"user_message\":\"Hello\"}'
```

> The cookie value never reaches Fly secrets and is **not logged** by the agent — it is forwarded **only** to `{OPENEMR_BASE_URL}/api/user` for the lifetime of the request.

## Demo bypass mode (NOT for production)

> **WARNING: Demo bypass active.** When `AGENT_DEMO_BYPASS=1` **and** the request carries `X-Agent-Demo-Role: PHYSICIAN|NURSE|ADMIN`, the agent **skips OpenEMR session validation entirely** and trusts the supplied role. Use this **only** for non-PHI demos against a throwaway environment. Never enable in real PHI environments. Either condition alone (env var without header, or header without env var) leaves the normal `Authorization` / `Cookie` validation path unchanged.
>
> Default behavior with the env var unset is byte-identical to before: the `X-Agent-Demo-Role` header is ignored and OpenEMR validation is still required.

Enable on Fly:

```bash
fly secrets set AGENT_DEMO_BYPASS=1 --app clinical-agent-scaffold
# Disable later:
# fly secrets unset AGENT_DEMO_BYPASS --app clinical-agent-scaffold
```

PowerShell smoke (PS 7+ recommended; on Windows PS 5.1, use `curl.exe` not the `curl` alias):

```powershell
curl.exe -fsS -X POST "https://clinical-agent-scaffold.fly.dev/agent/chat" `
  -H "Content-Type: application/json" `
  -H "X-Agent-Demo-Role: PHYSICIAN" `
  -d '{\"patient_id\":\"1\",\"messages\":[],\"user_message\":\"Hello from demo bypass\"}'
```

When the bypass fires, the agent emits a structured `agent_event` line with `event_type=auth_demo_bypass` (see the operator triage table below). Raw `Authorization` and `Cookie` values are **never** logged on this path — only the resolved role and a fixed reason string.

### PowerShell (`scripts/smoke_agent_service.ps1`)

Use **PowerShell 7+** (`pwsh`) when you pass **`-AuthHeader`** (chat smoke). The script relies on `Invoke-WebRequest -SkipHttpErrorCheck`, which exists only in PS 7+; on **Windows PowerShell 5.1**, non-2xx chat responses may **throw** before status checks, so behavior differs from PS 7. Health-only (`-BaseUrl` only) is usually fine on 5.1.

From the **repository root** (so `scripts\` resolves). Health only:

```powershell
.\scripts\smoke_agent_service.ps1 -BaseUrl "https://clinical-agent-scaffold.fly.dev"
```

Health **and** authenticated chat (pass a raw token or a full `Bearer <token>` string):

```powershell
.\scripts\smoke_agent_service.ps1 `
  -BaseUrl "https://clinical-agent-scaffold.fly.dev" `
  -AuthHeader "Bearer <paste-from-browser-openemr-request>"
```

The script always runs `GET {BaseUrl}/agent/health`. When `-AuthHeader` is non-empty, it also runs `POST {BaseUrl}/agent/chat` with a small JSON body. Exit code `1` on failure.

### Bash (`scripts/smoke_agent_service.sh`)

From the **repository root** (so `./scripts/` resolves). Health only:

```bash
./scripts/smoke_agent_service.sh --base-url "https://clinical-agent-scaffold.fly.dev"
```

Health **and** authenticated chat (pass a raw token or a full `Bearer <token>` string; the script normalizes bare tokens to `Bearer …`):

```bash
./scripts/smoke_agent_service.sh \
  --base-url "https://clinical-agent-scaffold.fly.dev" \
  --auth-header "Bearer <paste-from-browser-openemr-request>"
```

The script always runs `GET {base}/agent/health`. When `--auth-header` is set, it also runs `POST {base}/agent/chat`. Exit code `1` on failure.

**JSON for chat:** If you use `--auth-header`, you need **`jq` or `python3`** on your `PATH` — the script uses one of them to build the JSON body for `POST /agent/chat` (see `scripts/smoke_agent_service.sh`).

## Operator triage (structured logs)

Production logs use JSON-friendly **`event` / `event_type`** fields on `agent_event` lines (and matching extras on RBAC `tool_refusal` lines). Use **`fly logs --app <app>`** (or your log stack) and filter on these values.

| `event_type` | What it means | What to check |
|----------------|----------------|----------------|
| `openemr_misconfiguration` | `OPENEMR_BASE_URL` unset or empty at runtime. | `fly secrets list`; set `OPENEMR_BASE_URL` to the OpenEMR HTTPS origin; redeploy if needed. Logs include **`client_request_id`** when the caller sent **`X-Request-ID`**, **`X-Correlation-ID`**, or **`X-Trace-ID`** (first non-empty wins), else `none`. |
| `tool_refusal` | RBAC denied a tool for the session role. | `role`, `tool`, `what`/`why` in log extras; confirm USERS.md matrix vs caller. |
| `verify_failure` / `rgv_verify_retry` / `rgv_degraded_unverified` | RGV verify path: failed check, bounded retry, or returned **unverified** assistant text. | `why`, `verify_retry_count`, `duration_ms`, `fallback`; inspect upstream verify rules / model output. |
| `category_boundary_review` | Scaffold/lab signal: labs + vitals context in one turn (demo hook until fork validates FHIR `Observation.category`). | Treat as **review queue**, not a clinical assertion; correlate with real FHIR tagging in fork. |
| `chat_turn_complete` | Turn finished (happy or unverified). | `verified`, `rgv_duration_ms`, `fallback` (`none` vs `unverified_response`); `cost_envelope` is placeholder until billing hooks exist. |
| `auth_demo_bypass` | **Demo bypass active** — `AGENT_DEMO_BYPASS=1` AND `X-Agent-Demo-Role` short-circuited OpenEMR session validation. **Treat as misconfiguration in any PHI environment.** | `role` (the trusted demo role), `client_request_id`; in production, `fly secrets unset AGENT_DEMO_BYPASS --app <app>` immediately and rotate any data accessed during the bypass window. |

**GitHub Actions:** Manual deploy runs appear under **Actions** → **Fly agent (manual deploy)**; use the run timestamp and actor to correlate with `fly releases` / app logs after a deploy.

## Troubleshooting

| Symptom | Likely cause | What to do |
|--------|----------------|------------|
| **502 Bad Gateway** | Machine stopped (`min_machines_running = 0`), cold start, or process crash before accepting connections. | `fly logs --app <app>`; retry after a few seconds; consider `min_machines_running = 1` if you need always-on. |
| **502 / connection refused / health never passes** | **Wrong port** — `internal_port` or `PORT` in `fly.agent.toml` does not match Uvicorn’s listen port in `Dockerfile.agent`. | Re-read [Port alignment (8080)](#port-alignment-8080); fix Dockerfile **and** `fly.agent.toml` together, then redeploy. |
| **500 on `/agent/chat`**, health OK | **`OPENEMR_BASE_URL` missing or invalid** — server cannot reach or configure OpenEMR backend. | `fly secrets list --app <app>`; set `OPENEMR_BASE_URL` to the correct HTTPS origin; check logs for upstream errors. |

```bash
fly logs --app clinical-agent-scaffold
fly ssh console --app clinical-agent-scaffold
```

## Files involved

| File | Role |
|------|------|
| `Dockerfile.agent` | Production image: Python 3.12, Uvicorn on `0.0.0.0:8080`, non-root `appuser`. Optional **`IMAGE_SOURCE_URL`** build-arg sets `org.opencontainers.image.source` (defaults to a placeholder URL until you pass your canonical git remote). |
| `fly.agent.toml` | Fly app name, build `dockerfile` / `ignorefile`, **`[build.args].IMAGE_SOURCE_URL`** for OCI source label, `http_service.internal_port = 8080`, health check `GET /agent/health` |
| `deploy/requirements-agent.txt` | Runtime pip deps (`httpx`, `fastapi`, `python-dotenv`, `uvicorn[standard]`) |
| `.dockerignore.agent` | Smaller/faster agent image builds |
| `scripts/smoke_agent_service.ps1` | Local or remote smoke: health + optional chat with `-AuthHeader` (**use `pwsh` / PS 7+** for chat) |
| `scripts/smoke_agent_service.sh` | Same for Bash/macOS/Linux/Git Bash: `--base-url`, optional `--auth-header` (`jq` or `python3` when chat runs) |

## Local sanity (no server)

From repo root:

```bash
python -c "from agent.http.app import create_app; create_app(); print('ok')"
```

Or run Uvicorn:

```bash
uvicorn agent.http.app:create_app --factory --host 127.0.0.1 --port 8080
```

Then `curl http://127.0.0.1:8080/agent/health` in another terminal, or:

```powershell
.\scripts\smoke_agent_service.ps1 -BaseUrl "http://127.0.0.1:8080"
```
