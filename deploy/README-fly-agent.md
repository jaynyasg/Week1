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
| **`OPENEMR_BASE_URL` secret** | Required for `/agent/chat` (and tool routes that call OpenEMR). Set before relying on chat: `fly secrets set OPENEMR_BASE_URL=https://your-openemr-host.example.com --app <your-app>`. **`/agent/health` does not need this secret.** |

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
fly deploy --config fly.agent.toml --app clinical-agent-scaffold
```

Ensure `fly.agent.toml` has the same `app = "clinical-agent-scaffold"` or always pass `--app`.

## Secrets

```bash
fly secrets set OPENEMR_BASE_URL=https://your-openemr-host.example.com --app clinical-agent-scaffold
```

- No trailing slash required (the app normalizes it).
- Do **not** put OpenEMR cookies or bearer tokens in Fly secrets for generic chat; clients send `Authorization` per request. Only set additional secrets if you add features that need them.

## Smoke checks

### curl (from any shell)

Replace the hostname with your app name:

```bash
curl -fsS https://clinical-agent-scaffold.fly.dev/agent/health
# Expect JSON: {"status":"ok"}
```

**Optional** — `POST /agent/chat` against a **real** OpenEMR session (copy `Authorization` from your browser’s network tab while logged into OpenEMR, same as local dev):

```bash
curl -fsS -X POST "https://clinical-agent-scaffold.fly.dev/agent/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <paste-from-browser-openemr-request>" \
  -d "{\"patient_id\":\"1\",\"messages\":[],\"user_message\":\"Hello\"}"
```

### PowerShell (`scripts/smoke_agent_service.ps1`)

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
| `Dockerfile.agent` | Production image: Python 3.12, Uvicorn on `0.0.0.0:8080`, non-root `appuser` |
| `fly.agent.toml` | Fly app name, build `dockerfile = "Dockerfile.agent"`, `ignorefile = ".dockerignore.agent"`, `http_service.internal_port = 8080`, health check `GET /agent/health` |
| `deploy/requirements-agent.txt` | Runtime pip deps (`httpx`, `fastapi`, `python-dotenv`, `uvicorn[standard]`) |
| `.dockerignore.agent` | Smaller/faster agent image builds |
| `scripts/smoke_agent_service.ps1` | Local or remote smoke: health + optional chat with `-AuthHeader` |
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
