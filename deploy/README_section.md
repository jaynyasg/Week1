<!--
README_section.md — paste the contents below into your fork's README.md
under a top-level `## Deployment` heading. Replace {{DEPLOYED_URL}} with
the actual Fly URL printed at the end of `bash scripts/deploy_fly.sh`.
-->

## Deployment

This fork is deployed on **Fly.io** as two apps connected over Fly's private network:

- **OpenEMR (PHP/Apache)** — `clinical-copilot.fly.dev` — public HTTPS
- **MariaDB 10.11** — `clinical-copilot-db.internal` — private (Fly 6PN), not publicly reachable

Live URL: **{{DEPLOYED_URL}}**

### Deploy

```bash
# One-time
brew install flyctl                 # macOS; or: curl -L https://fly.io/install.sh | sh
fly auth login

# Every time (idempotent)
bash scripts/deploy_fly.sh
```

The script provisions both apps, creates persistent volumes, sets secrets, and deploys. First run takes ~5–10 minutes; the OpenEMR auto-installer needs ~3 minutes to seed the schema.

### Verify

```bash
DEPLOYED_URL={{DEPLOYED_URL}} pytest tests/integration/test_deployment.py -v
```

All seven smoke tests must pass before submitting any checkpoint.

### Full reference

See [`docs/deployment.md`](docs/deployment.md) for the architecture decision record, the runbook, and troubleshooting for every known failure mode.
