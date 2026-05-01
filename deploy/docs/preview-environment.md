# Preview / staging Fly apps (leave the production demo alone)

Use **separate Fly app names** so you can deploy the OpenEMR image with embedded UI, or a new agent revision, **without** touching the app your stakeholders use for demos.

## Pattern

| Environment | OpenEMR app example | Agent app example |
|-------------|---------------------|-------------------|
| Production demo | `clinical-copilot-v2` | `clinical-agent-scaffold` |
| Preview | `clinical-copilot-preview` | `clinical-agent-preview` |

## Steps (outline)

1. `fly apps create clinical-copilot-preview` (globally unique name).
2. Copy **`fly.toml`** / **`fly.agent.toml`** to preview variants **or** pass `--app` / `--config` on every command.
3. Create **new volumes** for preview (do not attach prod volumes to preview apps).
4. Set the same **classes** of secrets on preview (`OPENEMR_BASE_URL` on agent must point at **preview** OpenEMR URL, not prod).
5. In preview OpenEMR **`fly.toml` `[env]`**, set **`CLINICAL_AGENT_INTERNAL_URL=http://clinical-agent-preview.internal:8080`** (match your agent app name).

## Internal DNS

Fly 6PN hostnames are **`<app>.internal`**. The embedded Apache proxy must target the **preview** agent, not production, when testing preview OpenEMR.

## When preview is enough

- Validating **`Dockerfile.fly`** + **`openemr_wrapper.sh`** before rolling to prod.
- Load-testing or breaking **`AGENT_RATE_LIMIT_CHAT`** without affecting demo traffic.

See also [safe-rollout.md](safe-rollout.md).
