# Onboarding quick-check: Python/pytest versions and live-test env flags (no secrets).
Write-Host "== Week1 doctor (onboarding) =="
python --version
python -m pytest --version
if ($env:RUN_LIVE_OPENEMR_E2E) { Write-Host "RUN_LIVE_OPENEMR_E2E=$($env:RUN_LIVE_OPENEMR_E2E)" }
else { Write-Host "RUN_LIVE_OPENEMR_E2E=<unset>" }
if ($env:RUN_LIVE_OPENEMR_TESTS) { Write-Host "RUN_LIVE_OPENEMR_TESTS=$($env:RUN_LIVE_OPENEMR_TESTS)" }
else { Write-Host "RUN_LIVE_OPENEMR_TESTS=<unset>" }
