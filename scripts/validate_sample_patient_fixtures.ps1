# Validate fixtures/sample-patients CSVs (no database). Pass -Quick for CI-fast check.
param(
    [switch] $Quick,
    [string] $Root = ""
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    $pyArgs = @("scripts/validate_sample_patient_fixtures.py")
    if ($Quick) { $pyArgs += "--quick" }
    if ($Root) { $pyArgs += @("--root", $Root) }
    python @pyArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
