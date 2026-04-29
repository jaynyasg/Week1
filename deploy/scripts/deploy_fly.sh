#!/usr/bin/env bash
# deploy_fly.sh — one-shot Fly.io deploy for the Clinical Co-Pilot stack.
#
# Idempotent: safe to re-run. Skips creation of apps/volumes/secrets that
# already exist. Re-runs `fly deploy` on every invocation.
#
# Usage:
#   bash scripts/deploy_fly.sh
#
# Prerequisites:
#   - flyctl installed (https://fly.io/docs/flyctl/install/)
#   - `fly auth login` completed
#   - fly.toml and fly.db.toml present at repo root

set -euo pipefail

OPENEMR_APP="clinical-copilot"
DB_APP="clinical-copilot-db"
REGION="iad"
VOL_SIZE_GB=3

bold()   { printf "\n\033[1m== %s ==\033[0m\n" "$*"; }
warn()   { printf "\033[33m!! %s\033[0m\n" "$*"; }
fail()   { printf "\033[31mxx %s\033[0m\n" "$*" >&2; exit 1; }

# ── 0. Sanity checks ───────────────────────────────────────────────────────
command -v fly >/dev/null 2>&1 || fail "flyctl not installed. https://fly.io/docs/flyctl/install/"
fly auth whoami >/dev/null 2>&1 || fail "Not logged in. Run: fly auth login"
[[ -f fly.toml ]]    || fail "fly.toml not found at repo root."
[[ -f fly.db.toml ]] || fail "fly.db.toml not found at repo root."

# ── 1. Database app ────────────────────────────────────────────────────────
bold "Database app: $DB_APP"
if fly apps list | grep -q "^$DB_APP\b"; then
  warn "App $DB_APP already exists — skipping create."
else
  fly apps create "$DB_APP"
fi

if fly volumes list --app "$DB_APP" | grep -q "mariadb_data"; then
  warn "Volume mariadb_data already exists — skipping create."
else
  fly volumes create mariadb_data --app "$DB_APP" --region "$REGION" --size "$VOL_SIZE_GB" --yes
fi

if ! fly secrets list --app "$DB_APP" | grep -q "MYSQL_ROOT_PASSWORD"; then
  bold "Setting database secrets"
  DB_ROOT_PW=$(openssl rand -hex 24)
  DB_USER_PW=$(openssl rand -hex 24)
  fly secrets set --app "$DB_APP" --stage \
    MYSQL_ROOT_PASSWORD="$DB_ROOT_PW" \
    MYSQL_DATABASE=openemr \
    MYSQL_USER=openemr \
    MYSQL_PASSWORD="$DB_USER_PW"
else
  warn "Database secrets already set — leaving them alone."
fi

bold "Deploying $DB_APP"
fly deploy --config fly.db.toml --app "$DB_APP" --wait-timeout 300

# ── 2. OpenEMR app ─────────────────────────────────────────────────────────
bold "OpenEMR app: $OPENEMR_APP"
if fly apps list | grep -q "^$OPENEMR_APP\b"; then
  warn "App $OPENEMR_APP already exists — skipping create."
else
  fly apps create "$OPENEMR_APP"
fi

if fly volumes list --app "$OPENEMR_APP" | grep -q "openemr_sites"; then
  warn "Volume openemr_sites already exists — skipping create."
else
  fly volumes create openemr_sites --app "$OPENEMR_APP" --region "$REGION" --size "$VOL_SIZE_GB" --yes
fi

if ! fly secrets list --app "$OPENEMR_APP" | grep -q "MYSQL_PASS\b"; then
  bold "Wiring OpenEMR to the database"
  # Pull the db-side secrets so OpenEMR can talk to MariaDB.
  DB_USER_PW=$(fly ssh console --app "$DB_APP" -C "printenv MYSQL_PASSWORD"     | tr -d '\r\n')
  DB_ROOT_PW=$(fly ssh console --app "$DB_APP" -C "printenv MYSQL_ROOT_PASSWORD" | tr -d '\r\n')
  OE_PASS_GEN=$(openssl rand -hex 16)

  fly secrets set --app "$OPENEMR_APP" --stage \
    MYSQL_HOST="$DB_APP.internal" \
    MYSQL_ROOT_PASS="$DB_ROOT_PW" \
    MYSQL_USER=openemr \
    MYSQL_PASS="$DB_USER_PW" \
    MYSQL_DATABASE=openemr \
    OE_USER=admin \
    OE_PASS="$OE_PASS_GEN"

  printf "\n\033[1mInitial admin password (save this — it will not be shown again):\033[0m\n"
  printf "  user: admin\n  pass: %s\n\n" "$OE_PASS_GEN"
else
  warn "OpenEMR secrets already set — leaving them alone."
fi

bold "Deploying $OPENEMR_APP (first boot can take 3–5 min while installer runs)"
fly deploy --config fly.toml --app "$OPENEMR_APP" --wait-timeout 600

# ── 3. Verify ──────────────────────────────────────────────────────────────
bold "Status"
fly status --app "$OPENEMR_APP"

URL="https://${OPENEMR_APP}.fly.dev"
printf "\n\033[1;32mDeployed:\033[0m %s\n" "$URL"
printf "Smoke test it:\n"
printf "  DEPLOYED_URL=%s pytest tests/integration/test_deployment.py\n\n" "$URL"
