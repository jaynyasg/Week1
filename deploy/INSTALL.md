# Fly.io Deployment Pack — Clinical Co-Pilot (PR-02)

This folder contains every file PR-02 needs. Copy them into your OpenEMR fork at the paths shown, then run the deploy commands at the bottom.

## File-to-destination map

Each file in this `deploy/` folder maps to a path inside your forked OpenEMR repo:

| File in `deploy/` | Copy to (inside openemr fork) |
|---|---|
| `docker-compose.prod.yml` | `docker-compose.prod.yml` (repo root) |
| `fly.toml` | `fly.toml` (repo root) |
| `fly.db.toml` | `fly.db.toml` (repo root) |
| `Dockerfile.fly` | `Dockerfile.fly` (repo root) |
| `.env.example` | `.env.example` (repo root) |
| `scripts/deploy_fly.sh` | `scripts/deploy_fly.sh` |
| `docs/deployment.md` | `docs/deployment.md` |
| `tests/integration/test_deployment.py` | `tests/integration/test_deployment.py` |
| `README_section.md` | Paste contents into your `README.md` under a `## Deployment` heading |

## Architecture

Two Fly apps, internal-DNS-connected, MariaDB never exposed to the public internet:

```
                                  Internet (HTTPS)
                                        │
                                        ▼
                            ┌─────────────────────┐
                            │  Fly app:           │
                            │  clinical-copilot   │  ← OpenEMR (PHP/Apache)
                            │  fly.toml           │     openemr/openemr image
                            └──────────┬──────────┘     Volume: openemr_sites
                                       │
                          .internal DNS (private 6PN)
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │  Fly app:           │
                            │  clinical-copilot-  │  ← MariaDB 10.11
                            │  db                 │     mariadb image
                            │  fly.db.toml        │     Volume: mariadb_data
                            └─────────────────────┘     NO public service block
```

Why two apps and not one container with both processes:
- Volumes attach per-app, so a separate db app means MariaDB persistence is isolated from OpenEMR.
- A redeploy of the OpenEMR app does not touch the database.
- The db app has no `[http_service]` block, so the only way to reach MariaDB is via `clinical-copilot-db.internal:3306` from inside Fly's private network. Public scans of port 3306 will be refused — satisfies the PR-02 security check.

## One-shot deploy commands

```bash
# 0. Inside your openemr fork after copying the files above
cd ~/code/openemr-fork

# 1. Install flyctl if you haven't
brew install flyctl   # macOS
# or: curl -L https://fly.io/install.sh | sh

# 2. Log in
fly auth login

# 3. Create the database app first (volume + secrets, no deploy yet)
fly apps create clinical-copilot-db
fly volumes create mariadb_data --app clinical-copilot-db --region iad --size 3
fly secrets set --app clinical-copilot-db \
  MYSQL_ROOT_PASSWORD="$(openssl rand -hex 24)" \
  MYSQL_DATABASE=openemr \
  MYSQL_USER=openemr \
  MYSQL_PASSWORD="$(openssl rand -hex 24)"
fly deploy --config fly.db.toml

# 4. Create the OpenEMR app
fly apps create clinical-copilot
fly volumes create openemr_sites --app clinical-copilot --region iad --size 3

# 5. Pull the db credentials so the OpenEMR app can use them
DB_PASSWORD=$(fly ssh console --app clinical-copilot-db -C "printenv MYSQL_PASSWORD" | tr -d '\r\n')
DB_ROOT_PASSWORD=$(fly ssh console --app clinical-copilot-db -C "printenv MYSQL_ROOT_PASSWORD" | tr -d '\r\n')

fly secrets set --app clinical-copilot \
  MYSQL_HOST=clinical-copilot-db.internal \
  MYSQL_ROOT_PASS="$DB_ROOT_PASSWORD" \
  MYSQL_USER=openemr \
  MYSQL_PASS="$DB_PASSWORD" \
  MYSQL_DATABASE=openemr \
  OE_USER=admin \
  OE_PASS="$(openssl rand -hex 16)"

# 6. Deploy OpenEMR
fly deploy --config fly.toml

# 7. Print the public URL
fly status --app clinical-copilot
# → URL is something like https://clinical-copilot.fly.dev

# 8. Print the admin password (you'll need it for the demo video)
fly secrets list --app clinical-copilot
# OE_PASS won't print the value — pull it from your shell history or set a known one above
```

**First boot will take 3–5 minutes** while OpenEMR's auto-installer creates the schema and seeds tables. Watch with `fly logs --app clinical-copilot`.

## After deploy: verify and submit

```bash
# Smoke tests
DEPLOYED_URL=https://clinical-copilot.fly.dev pytest tests/integration/test_deployment.py

# Update README.md with the live URL (search for {{DEPLOYED_URL}} placeholder)

# Commit the deployment artifacts
git add docker-compose.prod.yml fly.toml fly.db.toml Dockerfile.fly \
        .env.example scripts/deploy_fly.sh docs/deployment.md \
        tests/integration/test_deployment.py README.md
git commit -m "PR-02: Fly.io cloud deployment + smoke tests"
```

## Rollback / teardown

```bash
fly apps destroy clinical-copilot
fly apps destroy clinical-copilot-db
# Volumes are destroyed with the apps. PHI on volumes is gone after this.
```

## Known limitations (for ARCHITECTURE.md / docs/deployment.md)

- **Single region (iad).** Multi-region needs separate volumes per region — out of scope for MVP.
- **Volumes are not backed up by default.** Add `fly volumes snapshots create` to a cron before going to real PHI.
- **OpenEMR auto-installer runs on first boot only.** If you destroy the volume but not the app, you'll get a "sites already configured" error. Solution: destroy both or wipe the volume.
- **Demo data seeding** is a follow-up — handled by `scripts/seed_demo_data.sh` from PR-01, not by this deploy.
