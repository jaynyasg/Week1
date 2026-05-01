<#
.SYNOPSIS
  Smoke-test the local agent HTTP service (health, optional authenticated chat).

.NOTES
  For -AuthHeader (chat): use PowerShell 7+ (pwsh). PS 5.1 lacks SkipHttpErrorCheck on Invoke-WebRequest, so errors may throw before status checks.

.DESCRIPTION
  GET {BaseUrl}/agent/health always runs.
  When -AuthHeader is set, POST {BaseUrl}/agent/chat with a JSON body matching ChatRequest
  (patient_id, user_message, messages). Prints HTTP status codes; exits 1 on failure.

.PARAMETER AuthHeader
  OpenEMR bearer token value, or a full "Bearer <token>" string (used as Authorization header).

.PARAMETER PatientId
  Optional for chat; defaults to "smoke-test-patient" when -AuthHeader is set.

.PARAMETER UserMessage
  Optional for chat; defaults to "smoke: hello from smoke_agent_service.ps1" when -AuthHeader is set.
#>
[CmdletBinding()]
param(
    [string] $BaseUrl = "http://127.0.0.1:8080",
    [string] $AuthHeader = "",
    [string] $PatientId = "",
    [string] $UserMessage = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AuthorizationHeaderValue {
    param([string] $Raw)
    if ([string]::IsNullOrWhiteSpace($Raw)) { return $null }
    $t = $Raw.Trim()
    if ($t -match '^(?i)Bearer\s+') { return $t }
    return "Bearer $t"
}

function Invoke-AgentWebRequest {
    param(
        [string] $Uri,
        [string] $Method,
        [hashtable] $Headers = @{},
        [string] $Body = $null
    )
    $params = @{
        Uri             = $Uri
        Method          = $Method
        UseBasicParsing = $true
    }
    if ($Headers.Count -gt 0) {
        $params["Headers"] = $Headers
    }
    if ($null -ne $Body -and $Body.Length -gt 0) {
        $params["Body"] = $Body
        $params["ContentType"] = "application/json; charset=utf-8"
    }
    # PS 7+: inspect non-success status without throwing
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        $params["SkipHttpErrorCheck"] = $true
    }
    return Microsoft.PowerShell.Utility\Invoke-WebRequest @params
}

function Test-HttpSuccess {
    param([int] $StatusCode)
    return ($StatusCode -ge 200 -and $StatusCode -le 299)
}

$base = $BaseUrl.TrimEnd("/")
$failed = $false

try {
    $healthUri = "$base/agent/health"
    $health = Invoke-AgentWebRequest -Uri $healthUri -Method "GET"
    Write-Host "GET $healthUri -> $($health.StatusCode)"
    if (-not (Test-HttpSuccess -StatusCode $health.StatusCode)) {
        Write-Host "FAIL: health check returned non-success status." -ForegroundColor Red
        $failed = $true
    }
}
catch {
    Write-Host "FAIL: GET /agent/health -> $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if (-not [string]::IsNullOrWhiteSpace($AuthHeader)) {
    $defaultPatientId = "smoke-test-patient"
    $defaultUserMessage = "smoke: hello from smoke_agent_service.ps1"
    $effectivePatient = if ([string]::IsNullOrWhiteSpace($PatientId)) { $defaultPatientId } else { $PatientId.Trim() }
    $effectiveMessage = if ([string]::IsNullOrWhiteSpace($UserMessage)) { $defaultUserMessage } else { $UserMessage.Trim() }

    if ($effectivePatient.Length -lt 1 -or $effectiveMessage.Length -lt 1) {
        Write-Host "FAIL: patient_id and user_message must be non-empty for ChatRequest." -ForegroundColor Red
        exit 1
    }

    $chatBody = @{
        patient_id   = $effectivePatient
        user_message = $effectiveMessage
        messages     = @()
    } | ConvertTo-Json -Compress

    $authValue = Get-AuthorizationHeaderValue -Raw $AuthHeader
    $headers = @{ Authorization = $authValue }

    try {
        $chatUri = "$base/agent/chat"
        $chat = Invoke-AgentWebRequest -Uri $chatUri -Method "POST" -Headers $headers -Body $chatBody
        Write-Host "POST $chatUri -> $($chat.StatusCode)"
        if (-not (Test-HttpSuccess -StatusCode $chat.StatusCode)) {
            Write-Host "FAIL: chat returned non-success status." -ForegroundColor Red
            $failed = $true
        }
    }
    catch {
        Write-Host "FAIL: POST /agent/chat -> $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

if ($failed) {
    exit 1
}

exit 0
