#!/usr/bin/env bash
# Optional smoke checks against any agent base URL.
# Usage: bash scripts/smoke_agent_optional.sh --base-url https://clinical-agent-scaffold.fly.dev
set -euo pipefail

BASE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE="${2:-}"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$BASE" ]]; then
  echo "Usage: $0 --base-url https://your-agent.fly.dev"
  exit 1
fi

BASE="${BASE%/}"

curl -fsS "$BASE/agent/health" | grep -q ok
curl -fsS "$BASE/agent/health/ready" | grep -q ready
curl -fsS "$BASE/agent/metrics" | grep -q clinical_agent_up

echo "OK: health, ready, metrics at $BASE"
