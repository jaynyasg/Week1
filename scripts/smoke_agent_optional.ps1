<#
.SYNOPSIS
  Optional smoke checks against any agent base URL (no secrets in script).

.PARAMETER BaseUrl
  HTTPS origin of the FastAPI agent, e.g. https://clinical-agent-scaffold.fly.dev

.EXAMPLE
  .\scripts\smoke_agent_optional.ps1 -BaseUrl "https://clinical-agent-scaffold.fly.dev"
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$BaseUrl
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")

$health = Invoke-WebRequest -Uri "$base/agent/health" -UseBasicParsing -TimeoutSec 30
if ($health.StatusCode -ne 200) { throw "health: expected 200, got $($health.StatusCode)" }

$ready = Invoke-WebRequest -Uri "$base/agent/health/ready" -UseBasicParsing -TimeoutSec 30
if ($ready.StatusCode -ne 200) { throw "ready: expected 200, got $($ready.StatusCode)" }

$m = Invoke-WebRequest -Uri "$base/agent/metrics" -UseBasicParsing -TimeoutSec 30
if ($m.StatusCode -ne 200) { throw "metrics: expected 200" }
if ($m.Content -notmatch "clinical_agent_up") { throw "metrics: missing clinical_agent_up" }

Write-Host "OK: health, ready, metrics at $base"
