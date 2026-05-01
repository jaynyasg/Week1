# Dependency security audits

Run these periodically (for example before a production rollout or monthly). They complement code review and do not replace threat modeling for PHI.

## Python

From the repository root:

```bash
python -m pip install pip-audit
python -m pip_audit -r requirements.txt
python -m pip_audit -r deploy/requirements-agent.txt
```

## Node (chat UI)

```bash
cd chat-ui
npm audit
```

## Last recorded scan (local dev machine)

| Scope | Command | Result | Date (UTC) |
|-------|---------|--------|------------|
| Root Python | `pip_audit -r requirements.txt` | No known vulnerabilities reported | 2026-05-01 |
| Agent image Python | `pip_audit -r deploy/requirements-agent.txt` | No known vulnerabilities reported | 2026-05-01 |
| `chat-ui` | `npm audit` | 2 **moderate**: `esbuild` (via `vite`) — dev-server request issue ([GHSA-67mh-4wv8-2f99](https://github.com/advisories/GHSA-67mh-4wv8-2f99)). Fix path suggested by npm is a **breaking** Vite major upgrade. | 2026-05-01 |

## CI (non-blocking)

GitHub Actions **Agent tests** workflow includes **`pip-audit`** and **`npm audit`** jobs with **`continue-on-error: true`** so default merges are not blocked; review logs when those jobs warn.

GitLab **dependency-audit** and **npm-audit-chat-ui** jobs use **`allow_failure: true`** for the same reason.

**Note on the npm findings:** Production ships static assets built with `vite build`; the vulnerable code path is the **development** server. Treat as lower risk for deployed OpenEMR embeds that never expose `vite dev` to untrusted networks. Still plan a controlled Vite upgrade when feasible.
