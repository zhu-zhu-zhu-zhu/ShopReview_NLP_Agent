param(
    [Parameter(Mandatory = $true)]
    [string]$ReviewPath,

    [Parameter(Mandatory = $true)]
    [string]$MetaPath
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Inspector = Join-Path $RepoRoot 'src\data\inspect_amazon_fashion.py'

try {
    if (-not (Test-Path -LiteralPath $ReviewPath -PathType Leaf)) {
        throw "Review JSONL file not found: $ReviewPath"
    }
    if (-not (Test-Path -LiteralPath $MetaPath -PathType Leaf)) {
        throw "Metadata JSONL file not found: $MetaPath"
    }
    if (-not (Test-Path -LiteralPath $Inspector -PathType Leaf)) {
        throw "Inspection program not found: $Inspector"
    }

    $RequiredDirectories = @(
        (Join-Path $RepoRoot 'reports\data_inspection'),
        (Join-Path $RepoRoot 'docs'),
        (Join-Path $RepoRoot 'data\sample\amazon_fashion'),
        (Join-Path $RepoRoot 'data\state\inspection')
    )
    foreach ($Directory in $RequiredDirectories) {
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    }

    Push-Location $RepoRoot
    try {
        & python $Inspector `
            --review-path $ReviewPath `
            --meta-path $MetaPath `
            --output-json 'reports/data_inspection/amazon_fashion_sample_profile.json' `
            --output-report 'docs/DATA_INSPECTION_REPORT.md' `
            --sample-dir 'data/sample/amazon_fashion' `
            --sample-size 100 `
            --seed 42 `
            --max-review-lines 100000 `
            --max-meta-lines 50000 `
            --progress-every 10000
        if ($LASTEXITCODE -ne 0) {
            throw "Python inspection exited with code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "BOUNDED DATA INSPECTION RUNNER: PASS"
    exit 0
}
catch {
    Write-Error $_
    Write-Host "BOUNDED DATA INSPECTION RUNNER: FAIL"
    exit 1
}
