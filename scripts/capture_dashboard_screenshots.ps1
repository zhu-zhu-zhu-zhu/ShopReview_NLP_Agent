[CmdletBinding()]
param(
    [string]$FrontendUrl = "http://127.0.0.1:5173",
    [string]$HealthUrl = "http://127.0.0.1:8080/api/health"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DashboardRoot = Join-Path $ProjectRoot "dashboard"

function Assert-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 8
        if ($response.StatusCode -ne 200) {
            throw "HTTP $($response.StatusCode)"
        }
    }
    catch {
        throw "$Name is unavailable at $Url. Start the backend and dashboard first. $($_.Exception.Message)"
    }
}

Write-Host "[1/3] Verify warehouse backend"
Assert-HttpEndpoint -Url $HealthUrl -Name "Warehouse backend"

Write-Host "[2/3] Verify dashboard"
Assert-HttpEndpoint -Url $FrontendUrl -Name "Dashboard"

Write-Host "[3/3] Capture production dashboard screenshots"
Push-Location $DashboardRoot
try {
    & npm.cmd run screenshots -- --url $FrontendUrl --health-url $HealthUrl
    if ($LASTEXITCODE -ne 0) {
        throw "Dashboard screenshot command failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Screenshots: $ProjectRoot\screenshots\dashboard"
