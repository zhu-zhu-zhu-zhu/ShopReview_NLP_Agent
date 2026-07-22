[CmdletBinding()]
param(
    [string]$InputPath = 'D:\bdt-app-course\projects\ShopReview_NLP_Agent\data\processed\nlp_production_v1\nlp_input_prod_v1.jsonl',
    [string]$ModelVersion = 'tfidf_logreg_v1',
    [string]$PredictionModelVersion = 'tfidf_logreg_oof_v1',
    [string]$ExpectedSha256 = 'e10925187eea5fc34721778c0a6e2ea5b8c7492a1325fd0c49966dafe3f12714',
    [int]$ExpectedRowCount = 99703,
    [switch]$ValidateOnly,
    [switch]$SkipInstall,
    [switch]$SkipTraining
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$PredictionPath = Join-Path $RepoRoot "data\processed\nlp_predictions_production_v1\predictions_$PredictionModelVersion.jsonl"
$MetricsPath = Join-Path $RepoRoot "reports\nlp\${ModelVersion}_metrics.json"
$ManifestPath = Join-Path $RepoRoot "reports\nlp\${ModelVersion}_model_manifest.json"
$SummaryPath = Join-Path $RepoRoot "reports\nlp\${PredictionModelVersion}_prediction_summary.json"
$ModelPath = Join-Path $RepoRoot "models\${ModelVersion}.joblib"

function Invoke-CheckedPython {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CommandArgs)
    & $PythonPath @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE"
    }
}

try {
    Write-Host '[1/6] Branch, input and hash safety'
    $CurrentBranch = (& git -C $RepoRoot symbolic-ref --short HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Unable to determine current Git branch' }
    if ($CurrentBranch -ne 'nlp-model-dev') { throw "Required branch is nlp-model-dev; current branch is $CurrentBranch" }
    if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) { throw "Input file not found: $InputPath" }
    $ActualHash = (Get-FileHash -LiteralPath $InputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualHash -ne $ExpectedSha256.ToLowerInvariant()) { throw "Input SHA-256 mismatch: $ActualHash" }

    Write-Host '[2/6] Isolated Python environment'
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        python -m venv (Join-Path $RepoRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create .venv' }
    }
    if (-not $SkipInstall) {
        Invoke-CheckedPython -CommandArgs @('-m', 'pip', 'install', '-r', (Join-Path $RepoRoot 'requirements-nlp.txt'))
    }
    Invoke-CheckedPython -CommandArgs @('-c', 'import numpy, sklearn, joblib, matplotlib; print("NLP dependencies: PASS")')

    Write-Host '[3/6] Synthetic unit tests'
    Push-Location $RepoRoot
    try {
        Invoke-CheckedPython -CommandArgs @('-m', 'unittest', 'tests.nlp.test_tfidf_logreg_pipeline', '-v')
    }
    finally {
        Pop-Location
    }

    if ($ValidateOnly -or $SkipTraining) {
        Write-Host '[4/6] Existing artifact validation only'
        foreach ($RequiredPath in @($PredictionPath, $MetricsPath, $ManifestPath, $ModelPath)) {
            if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) { throw "Required existing artifact not found: $RequiredPath" }
        }
        Push-Location $RepoRoot
        try {
            Invoke-CheckedPython -CommandArgs @(
                '-m', 'src.nlp.train_tfidf_logreg_v1',
                '--input-path', $InputPath,
                '--output-dir', (Join-Path $RepoRoot 'reports\nlp'),
                '--model-dir', (Join-Path $RepoRoot 'models'),
                '--model-version', $ModelVersion,
                '--prediction-model-version', $PredictionModelVersion,
                '--expected-sha256', $ExpectedSha256,
                '--expected-row-count', [string]$ExpectedRowCount,
                '--skip-training'
            )
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Host '[4/6] Candidate selection, held-out evaluation and 5-fold OOF predictions'
        Push-Location $RepoRoot
        try {
            Invoke-CheckedPython -CommandArgs @(
                '-m', 'src.nlp.train_tfidf_logreg_v1',
                '--input-path', $InputPath,
                '--output-dir', (Join-Path $RepoRoot 'reports\nlp'),
                '--model-dir', (Join-Path $RepoRoot 'models'),
                '--model-version', $ModelVersion,
                '--prediction-model-version', $PredictionModelVersion,
                '--expected-sha256', $ExpectedSha256,
                '--expected-row-count', [string]$ExpectedRowCount,
                '--random-state', '42',
                '--max-features', '50000',
                '--min-df', '2',
                '--max-df', '0.98',
                '--ngram-max', '2',
                '--max-iter', '1000'
            )
        }
        finally {
            Pop-Location
        }
    }

    Write-Host '[5/6] Independent prediction contract validation'
    Push-Location $RepoRoot
    try {
        Invoke-CheckedPython -CommandArgs @(
            '-m', 'src.nlp.validate_prediction_output',
            '--input-path', $InputPath,
            '--prediction-path', $PredictionPath,
            '--output-summary', $SummaryPath,
            '--expected-model-version', $PredictionModelVersion,
            '--expected-row-count', [string]$ExpectedRowCount
        )
    }
    finally {
        Pop-Location
    }

    Write-Host '[6/6] Result'
    Write-Host 'NLP BASELINE TRAINING RESULT: PASS'
    Write-Host 'HELD-OUT TEST EVALUATION RESULT: PASS'
    Write-Host 'OOF PREDICTION GENERATION RESULT: PASS'
    Write-Host 'PREDICTION CONTRACT VALIDATION RESULT: PASS'
    Write-Host 'FULL MODEL ARTIFACT RESULT: PASS'
    Write-Host 'NLP BASELINE V1 RUNNER: PASS'
    exit 0
}
catch {
    Write-Error $_
    Write-Host 'NLP BASELINE TRAINING RESULT: FAIL'
    Write-Host 'HELD-OUT TEST EVALUATION RESULT: FAIL'
    Write-Host 'OOF PREDICTION GENERATION RESULT: FAIL'
    Write-Host 'PREDICTION CONTRACT VALIDATION RESULT: FAIL'
    Write-Host 'FULL MODEL ARTIFACT RESULT: FAIL'
    Write-Host 'NLP BASELINE V1 RUNNER: FAIL'
    exit 1
}
