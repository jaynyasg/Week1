#!/usr/bin/env bash
# Onboarding quick-check: Python/pytest versions and live-test env flags (no secrets).
set -euo pipefail
echo "== Week1 doctor (onboarding) =="
python --version
python -m pytest --version
if [[ -n "${RUN_LIVE_OPENEMR_E2E:-}" ]]; then
  echo "RUN_LIVE_OPENEMR_E2E=${RUN_LIVE_OPENEMR_E2E}"
else
  echo "RUN_LIVE_OPENEMR_E2E=<unset>"
fi
if [[ -n "${RUN_LIVE_OPENEMR_TESTS:-}" ]]; then
  echo "RUN_LIVE_OPENEMR_TESTS=${RUN_LIVE_OPENEMR_TESTS}"
else
  echo "RUN_LIVE_OPENEMR_TESTS=<unset>"
fi
