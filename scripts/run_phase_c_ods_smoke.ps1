param(
    [string]$ReviewSample = 'data\sample\amazon_fashion\reviews_sample_100.jsonl',
    [string]$MetaSample = 'data\sample\amazon_fashion\meta_sample_100.jsonl'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Converter = Join-Path $RepoRoot 'src\data\prepare_ods_smoke_data.py'
$OutputDir = Join-Path $RepoRoot 'data\processed\phase_c_smoke'
$ReviewOutput = Join-Path $OutputDir 'ods_review_smoke.txt'
$MetaOutput = Join-Path $OutputDir 'ods_meta_smoke.txt'
$CreateSql = Join-Path $RepoRoot 'sql\ods\01_create_amazon_fashion_ods_smoke.sql'
$ValidateSql = Join-Path $RepoRoot 'sql\validation\01_validate_amazon_fashion_ods_smoke.sql'
$NameNode = 'tier4_stu_namenode'
$HiveServer = 'tier4_stu_hiveserver2'
$JdbcUrl = 'jdbc:hive2://localhost:10000/default'
$ReviewHdfs = '/data/review_dw/smoke/ods_amazon_fashion_review'
$MetaHdfs = '/data/review_dw/smoke/ods_amazon_fashion_meta'

function Assert-ExitCode([string]$Stage) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Stage failed with exit code $LASTEXITCODE"
    }
}

function Get-HiveCount([string]$Query) {
    # Beeline writes harmless locale/SLF4J warnings to stderr in this image.
    # Count parsing intentionally consumes stdout only; LASTEXITCODE still enforces failures.
    $PreviousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $Output = @(& docker exec $HiveServer beeline --silent=true --showHeader=false --outputformat=tsv2 -u $JdbcUrl -e $Query 2>$null)
        $QueryExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorAction
    }
    if ($QueryExitCode -ne 0) {
        throw "Hive count query failed with exit code $QueryExitCode"
    }
    $NumericLines = @($Output | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ -match '^\d+$' })
    if ($NumericLines.Count -eq 0) {
        throw "Hive count query returned no numeric result: $Query"
    }
    return [int]$NumericLines[-1]
}

try {
    Push-Location $RepoRoot
    try {
        Write-Host '[1/8] Validating local sample files'
        if (-not (Test-Path -LiteralPath $ReviewSample -PathType Leaf)) {
            throw "Review sample not found: $ReviewSample"
        }
        if (-not (Test-Path -LiteralPath $MetaSample -PathType Leaf)) {
            throw "Metadata sample not found: $MetaSample"
        }

        Write-Host '[2/8] Converting JSONL samples to Hive-safe control-A text'
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        & python $Converter --review-sample $ReviewSample --meta-sample $MetaSample --output-dir $OutputDir
        Assert-ExitCode 'Sample conversion'

        Write-Host '[3/8] Verifying exactly 100 converted physical rows per file'
        $ReviewRows = @(Get-Content -LiteralPath $ReviewOutput).Count
        $MetaRows = @(Get-Content -LiteralPath $MetaOutput).Count
        if ($ReviewRows -ne 100 -or $MetaRows -ne 100) {
            throw "Converted row count mismatch: reviews=$ReviewRows metadata=$MetaRows"
        }
        Write-Host "Converted rows: reviews=$ReviewRows metadata=$MetaRows"

        Write-Host '[4/8] Checking Docker, HDFS and Hive services'
        docker version | Out-Null
        Assert-ExitCode 'Docker health check'
        docker exec $NameNode hdfs dfs -ls / | Out-Null
        Assert-ExitCode 'HDFS health check'
        docker exec $HiveServer beeline -u $JdbcUrl -e 'SHOW DATABASES;' | Out-Null
        Assert-ExitCode 'Hive health check'

        Write-Host '[5/8] Creating exact HDFS smoke directories'
        docker exec $NameNode hdfs dfs -mkdir -p $ReviewHdfs
        Assert-ExitCode 'Review HDFS directory creation'
        docker exec $NameNode hdfs dfs -mkdir -p $MetaHdfs
        Assert-ExitCode 'Metadata HDFS directory creation'

        Write-Host '[6/8] Uploading only converted 100-row smoke files'
        docker cp $ReviewOutput "${NameNode}:/tmp/ods_review_smoke.txt"
        Assert-ExitCode 'Review docker copy'
        docker cp $MetaOutput "${NameNode}:/tmp/ods_meta_smoke.txt"
        Assert-ExitCode 'Metadata docker copy'
        # -put -f replaces only the two exact smoke filenames; no other HDFS path is removed.
        docker exec $NameNode hdfs dfs -put -f '/tmp/ods_review_smoke.txt' $ReviewHdfs
        Assert-ExitCode 'Review HDFS upload'
        docker exec $NameNode hdfs dfs -put -f '/tmp/ods_meta_smoke.txt' $MetaHdfs
        Assert-ExitCode 'Metadata HDFS upload'

        Write-Host '[7/8] Creating review_dw and exact smoke external tables'
        docker cp $CreateSql "${HiveServer}:/tmp/01_create_amazon_fashion_ods_smoke.sql"
        Assert-ExitCode 'Create SQL docker copy'
        docker exec $HiveServer beeline -u $JdbcUrl -f '/tmp/01_create_amazon_fashion_ods_smoke.sql'
        Assert-ExitCode 'Hive ODS creation'

        Write-Host '[8/8] Running Hive validation SQL and enforcing exact row counts'
        $ReviewHiveCount = Get-HiveCount 'SELECT COUNT(*) FROM review_dw.ods_amazon_fashion_review_smoke;'
        $MetaHiveCount = Get-HiveCount 'SELECT COUNT(*) FROM review_dw.ods_amazon_fashion_meta_smoke;'
        Write-Host "Hive rows: reviews=$ReviewHiveCount metadata=$MetaHiveCount"
        if ($ReviewHiveCount -ne 100 -or $MetaHiveCount -ne 100) {
            throw "Hive row count mismatch: reviews=$ReviewHiveCount metadata=$MetaHiveCount"
        }
        docker cp $ValidateSql "${HiveServer}:/tmp/01_validate_amazon_fashion_ods_smoke.sql"
        Assert-ExitCode 'Validation SQL docker copy'
        docker exec $HiveServer beeline -u $JdbcUrl -f '/tmp/01_validate_amazon_fashion_ods_smoke.sql'
        Assert-ExitCode 'Hive validation SQL'
    }
    finally {
        Pop-Location
    }
    Write-Host 'PHASE C ODS SMOKE RUNNER: PASS'
    exit 0
}
catch {
    Write-Error $_
    Write-Host 'PHASE C ODS SMOKE RUNNER: FAIL'
    exit 1
}
