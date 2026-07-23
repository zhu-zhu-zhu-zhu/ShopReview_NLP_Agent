[CmdletBinding()]
param(
  [string]$BatchId='prod_v1_100k',
  [string]$ModelVersion='tfidf_logreg_oof_v1',
  [string]$EnvFile='.env.mysql.local',
  [switch]$ValidateOnly,
  [switch]$ExportOnly,
  [switch]$SkipTests
)

$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$HiveServer='tier4_stu_hiveserver2'
$Jdbc='jdbc:hive2://localhost:10000/default'
$ExpectedCounts=@{overview=1;daily=4137;product=76784}
$ExportSql=Join-Path $RepoRoot 'sql\export\01_export_production_dws_for_mysql.sql'
$SchemaSql=Join-Path $RepoRoot 'sql\mysql\01_create_shopreview_serving_schema.sql'
$LocalRoot=Join-Path $RepoRoot 'data\processed\mysql_serving_sync'
$SummaryPath=Join-Path $RepoRoot 'reports\mysql_serving\mysql_serving_sync_summary.json'
$PythonPath=if(Test-Path -LiteralPath (Join-Path $RepoRoot '.venv\Scripts\python.exe')){Join-Path $RepoRoot '.venv\Scripts\python.exe'}else{'python'}

function Assert-Exit([string]$Stage){
  if($LASTEXITCODE -ne 0){throw "$Stage failed with exit code $LASTEXITCODE"}
}

function Invoke-Python([string[]]$CommandArgs){
  & $PythonPath @CommandArgs
  Assert-Exit 'Python'
}

function Import-SafeEnvFile([string]$Path){
  if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw "MySQL environment file not found: $Path"}
  $Allowed=@(
    'SHOPREVIEW_MYSQL_HOST','SHOPREVIEW_MYSQL_PORT','SHOPREVIEW_MYSQL_DATABASE',
    'SHOPREVIEW_MYSQL_USER','SHOPREVIEW_MYSQL_PASSWORD'
  )
  foreach($RawLine in Get-Content -LiteralPath $Path){
    $Line=$RawLine.Trim()
    if(-not $Line -or $Line.StartsWith('#')){continue}
    if($Line -notmatch '^([A-Z0-9_]+)=(.*)$'){throw 'Invalid MySQL environment-file line'}
    $Name=$Matches[1]
    if($Allowed -notcontains $Name){throw "Unsupported MySQL environment variable: $Name"}
    [Environment]::SetEnvironmentVariable($Name,$Matches[2],'Process')
  }
}

function Get-HiveCounts{
  $Query=@"
USE review_dw;
SELECT 'overview',COUNT(*) FROM dws_sentiment_overview WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';
SELECT 'daily',COUNT(*) FROM dws_sentiment_daily WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';
SELECT 'product',COUNT(*) FROM dws_product_sentiment WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';
"@
  $Lines=@(& docker exec $HiveServer beeline -u $Jdbc --silent=true --showHeader=false --outputformat=tsv2 -e $Query 2>$null)
  Assert-Exit 'Hive production-count query'
  $Counts=@{}
  foreach($Line in $Lines){
    $Text=$Line.ToString().Trim()
    if($Text -match '^(overview|daily|product)\s+(\d+)$'){$Counts[$Matches[1]]=[int64]$Matches[2]}
  }
  foreach($Name in $ExpectedCounts.Keys){
    if(-not $Counts.ContainsKey($Name)){throw "Hive count missing for $Name"}
    if($Counts[$Name] -ne $ExpectedCounts[$Name]){throw "Hive $Name count mismatch: $($Counts[$Name]) != $($ExpectedCounts[$Name])"}
  }
  return $Counts
}

function Clear-ExactLocalExport{
  $ExpectedBase=[System.IO.Path]::GetFullPath($LocalRoot).TrimEnd('\')
  foreach($Name in @('overview','daily','product')){
    $Target=[System.IO.Path]::GetFullPath((Join-Path $LocalRoot $Name))
    if(-not $Target.StartsWith($ExpectedBase+'\',[System.StringComparison]::OrdinalIgnoreCase)){
      throw "Unsafe local export path: $Target"
    }
    if(Test-Path -LiteralPath $Target){Remove-Item -LiteralPath $Target -Recurse -Force}
    New-Item -ItemType Directory -Path $Target -Force|Out-Null
  }
}

function Invoke-HiveExport{
  foreach($Path in @(
    '/tmp/shopreview_mysql_export/overview',
    '/tmp/shopreview_mysql_export/daily',
    '/tmp/shopreview_mysql_export/product'
  )){
    & docker exec $HiveServer rm -rf -- $Path
    Assert-Exit "Remove exact Hive export directory $Path"
  }
  $SqlText=Get-Content -LiteralPath $ExportSql -Raw
  & docker exec $HiveServer beeline -u $Jdbc --silent=true --showHeader=false `
    --hiveconf "serving_batch_id=$BatchId" --hiveconf "serving_model_version=$ModelVersion" -e $SqlText
  Assert-Exit 'Hive DWS local export'
  Clear-ExactLocalExport
  foreach($Name in @('overview','daily','product')){
    $Source="${HiveServer}:/tmp/shopreview_mysql_export/$Name/."
    $Target=Join-Path $LocalRoot $Name
    & docker cp $Source $Target
    Assert-Exit "Copy $Name export"
  }
}

function Get-SyncArgs{
  return @(
    '-m','src.data.sync_hive_dws_to_mysql',
    '--overview-path',(Join-Path $LocalRoot 'overview'),
    '--daily-path',(Join-Path $LocalRoot 'daily'),
    '--product-path',(Join-Path $LocalRoot 'product'),
    '--batch-id',$BatchId,
    '--model-version',$ModelVersion,
    '--summary-path',$SummaryPath
  )
}

try{
  Write-Host '[1/7] Branch and parameter safety'
  $Branch=(& git -C $RepoRoot symbolic-ref --short HEAD).Trim()
  Assert-Exit 'Git branch inspection'
  if($Branch -ne 'data-dev'){throw "Required branch is data-dev; current branch is $Branch"}
  if($BatchId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'){throw 'Unsafe BatchId'}
  if($ModelVersion -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'){throw 'Unsafe ModelVersion'}
  if($ValidateOnly -and $ExportOnly){throw 'ValidateOnly and ExportOnly cannot be combined'}

  Write-Host '[2/7] Docker, Hive and production DWS counts'
  & docker version --format '{{.Server.Version}}'|Out-Null
  Assert-Exit 'Docker availability'
  $HiveCounts=Get-HiveCounts
  Write-Host "HiveCounts=$($HiveCounts.overview)/$($HiveCounts.daily)/$($HiveCounts.product)"

  Write-Host '[3/7] Synthetic unit tests'
  if(-not $SkipTests){
    Push-Location $RepoRoot
    try{Invoke-Python @('-m','unittest','tests.data.test_sync_hive_dws_to_mysql','-v')}
    finally{Pop-Location}
  }

  if(-not $ValidateOnly){
    Write-Host '[4/7] Exact-scope Hive export and local copy'
    Invoke-HiveExport
  }else{Write-Host '[4/7] ValidateOnly: existing local exports retained'}

  Write-Host '[5/7] Local export contract validation'
  $SyncArgs=Get-SyncArgs
  if($ExportOnly){
    Push-Location $RepoRoot
    try{Invoke-Python ($SyncArgs+@('--source-only'))}
    finally{Pop-Location}
    Write-Host '[6/7] ExportOnly: no MySQL connection or write'
    Write-Host '[7/7] Result'
    Write-Host 'HIVE DWS EXPORT RESULT: PASS'
    Write-Host 'LOCAL EXPORT VALIDATION RESULT: PASS'
    Write-Host 'MYSQL SERVING SYNC RESULT: PENDING'
    Write-Host 'HIVE MYSQL RECONCILIATION RESULT: PENDING'
    Write-Host 'CREDENTIAL SAFETY RESULT: PASS'
    exit 0
  }

  Write-Host '[6/7] MySQL environment and connector'
  $ResolvedEnvFile=if([System.IO.Path]::IsPathRooted($EnvFile)){$EnvFile}else{Join-Path $RepoRoot $EnvFile}
  Import-SafeEnvFile $ResolvedEnvFile
  $HostName=$env:SHOPREVIEW_MYSQL_HOST
  if([string]::IsNullOrWhiteSpace($HostName)){$HostName='127.0.0.1'}
  $Port=if($env:SHOPREVIEW_MYSQL_PORT){[int]$env:SHOPREVIEW_MYSQL_PORT}else{3306}
  $Database=if($env:SHOPREVIEW_MYSQL_DATABASE){$env:SHOPREVIEW_MYSQL_DATABASE}else{'shopreview_serving'}
  $User=$env:SHOPREVIEW_MYSQL_USER
  if($Database -ne 'shopreview_serving'){throw 'SHOPREVIEW_MYSQL_DATABASE must be shopreview_serving'}
  if([string]::IsNullOrWhiteSpace($User)){throw 'SHOPREVIEW_MYSQL_USER is required'}
  if([string]::IsNullOrWhiteSpace($env:SHOPREVIEW_MYSQL_PASSWORD)){throw 'SHOPREVIEW_MYSQL_PASSWORD is required'}
  if(-not(Test-NetConnection $HostName -Port $Port -InformationLevel Quiet)){throw "MySQL is unavailable at ${HostName}:$Port"}
  Invoke-Python @('-c','import mysql.connector; print("mysql connector: PASS")')

  if(-not $ValidateOnly){
    $MysqlClient=(Get-Command mysql -ErrorAction Stop).Source
    $PreviousMysqlPwd=$env:MYSQL_PWD
    try{
      $env:MYSQL_PWD=$env:SHOPREVIEW_MYSQL_PASSWORD
      Get-Content -LiteralPath $SchemaSql -Raw|& $MysqlClient "--host=$HostName" "--port=$Port" "--user=$User" '--default-character-set=utf8mb4'
      Assert-Exit 'MySQL serving schema creation'
    }finally{$env:MYSQL_PWD=$PreviousMysqlPwd}
  }
  $ModeArgs=if($ValidateOnly){@('--validate-only')}else{@()}
  Push-Location $RepoRoot
  try{
    Invoke-Python ($SyncArgs+@(
      '--host',$HostName,'--port',[string]$Port,'--database',$Database,'--user',$User,
      '--password-env','SHOPREVIEW_MYSQL_PASSWORD'
    )+$ModeArgs)
  }finally{Pop-Location}

  Write-Host '[7/7] Result'
  Write-Host 'HIVE DWS EXPORT RESULT: PASS'
  Write-Host 'LOCAL EXPORT VALIDATION RESULT: PASS'
  Write-Host 'MYSQL SERVING SYNC RESULT: PASS'
  Write-Host 'HIVE MYSQL RECONCILIATION RESULT: PASS'
  Write-Host 'CREDENTIAL SAFETY RESULT: PASS'
  exit 0
}catch{
  Write-Error $_
  Write-Host 'HIVE DWS EXPORT RESULT: FAIL'
  Write-Host 'LOCAL EXPORT VALIDATION RESULT: FAIL'
  Write-Host 'MYSQL SERVING SYNC RESULT: FAIL'
  Write-Host 'HIVE MYSQL RECONCILIATION RESULT: FAIL'
  Write-Host 'CREDENTIAL SAFETY RESULT: FAIL'
  exit 1
}
