[CmdletBinding()]
param(
  [string]$BatchId='prod_v1_100k',
  [string]$ModelVersion='tfidf_logreg_oof_v1',
  [string]$EnvFile='.env.mysql.local',
  [switch]$BuildHive,
  [switch]$SyncMysql,
  [switch]$ValidateOnly,
  [switch]$Package,
  [switch]$PackageOnly,
  [switch]$SkipTests,
  [string]$ResumeFromTable=''
)

$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$HiveContainer='tier4_stu_hiveserver2'
$MysqlContainer='shopreview_mysql'
$Jdbc='jdbc:hive2://127.0.0.1:10000/review_dw'
$Python=if(Test-Path (Join-Path $RepoRoot '.venv\Scripts\python.exe')){Join-Path $RepoRoot '.venv\Scripts\python.exe'}else{'python'}
$ExportRoot=Join-Path $RepoRoot 'data\processed\dashboard_dws_v2'
$SummaryPath=Join-Path $RepoRoot 'reports\mysql_serving\dashboard_dws_v2_sync_summary.json'
$HiveCountsPath=Join-Path $RepoRoot 'data\state\dashboard_dws_v2\hive_counts.json'
$ManifestPath=Join-Path $RepoRoot 'docs\MYSQL_SERVING_V2_TABLE_MANIFEST.md'
$HandoffRoot='D:\bdt-app-course\handoff\shopreview_mysql_v2'
$ShortNames=@('category','store','verified_purchase','rating_matrix','confidence','monthly','alerts','samples','aspects','reasons')
$AllTables=@('dws_sentiment_overview','dws_sentiment_daily','dws_product_sentiment','dws_category_sentiment','dws_store_sentiment','dws_verified_purchase_sentiment','dws_rating_prediction_matrix','dws_prediction_confidence','dws_monthly_sentiment','dws_sentiment_alerts','dws_review_samples','dws_aspect_summary','dws_negative_reasons')
$BuildTables=@('dws_category_sentiment','dws_store_sentiment','dws_verified_purchase_sentiment','dws_rating_prediction_matrix','dws_prediction_confidence','dws_monthly_sentiment','dws_sentiment_alerts','dws_review_samples','dws_aspect_summary','dws_negative_reasons')

function Assert-Exit([string]$Stage){if($LASTEXITCODE -ne 0){throw "$Stage failed with exit code $LASTEXITCODE"}}
function Invoke-Python([string[]]$CommandArgs){& $Python @CommandArgs; Assert-Exit 'Python command'}
function Import-SafeEnv([string]$Path){
  if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw "MySQL environment file not found: $Path"}
  $Allowed=@('SHOPREVIEW_MYSQL_HOST','SHOPREVIEW_MYSQL_PORT','SHOPREVIEW_MYSQL_DATABASE','SHOPREVIEW_MYSQL_USER','SHOPREVIEW_MYSQL_PASSWORD')
  foreach($Raw in Get-Content -LiteralPath $Path){
    $Line=$Raw.Trim(); if(-not $Line -or $Line.StartsWith('#')){continue}
    if($Line -notmatch '^([A-Z0-9_]+)=(.*)$'){throw 'Invalid environment-file line'}
    if($Allowed -notcontains $Matches[1]){throw "Unsupported environment variable: $($Matches[1])"}
    [Environment]::SetEnvironmentVariable($Matches[1],$Matches[2],'Process')
  }
}
function Invoke-HiveSql([string]$Path,[string]$Stage){
  $Sql=Get-Content -LiteralPath $Path -Raw
  $Sql=(($Sql -split "`r?`n")|Where-Object{$_ -notmatch '^\s*--'}|ForEach-Object{$_.TrimEnd()}) -join "`n"
  $Leaf=Split-Path -Leaf $Path
  $Statements=@($Sql -split ';'|ForEach-Object{$_.Trim()}|Where-Object{$_ -and $_ -notmatch '^(?i:USE|SET)\b'})
  $Number=0
  $AllOutput=@()
  foreach($RawStatement in $Statements){
    $Statement=$RawStatement.Trim(); if(-not $Statement){continue}
    if($Leaf -eq '03_create_dashboard_dws_v2.sql' -and $script:ResumeIndex -gt 0 -and
       $Statement -match '^(?i:CREATE TABLE IF NOT EXISTS|INSERT OVERWRITE TABLE|INSERT INTO TABLE)\s+(dws_[a-z_]+)\b'){
      $TargetIndex=[array]::IndexOf($BuildTables,$Matches[1])
      if($TargetIndex -ge 0 -and $TargetIndex -lt $script:ResumeIndex){Write-Host "SKIP_CHECKPOINT=$($Matches[1])"; continue}
    }
    if($Leaf -eq '03_create_dashboard_dws_v2.sql' -and $script:PreserveValidCategory -and
       $Statement -match '^(?i:CREATE TABLE IF NOT EXISTS|INSERT OVERWRITE TABLE)\s+dws_category_sentiment\b'){
      Write-Host 'SKIP_VALID=dws_category_sentiment'
      continue
    }
    $Number++
    Write-Host "$Stage statement $Number/$($Statements.Count)"
    $Output=@(& docker exec $HiveContainer beeline -u $Jdbc --database review_dw --silent=true --showHeader=false --outputformat=tsv2 --force=false `
      --hiveconf 'hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat' --hiveconf 'hive.merge.mapfiles=false' `
      --hiveconf 'hive.merge.mapredfiles=false' --hiveconf 'hive.merge.tezfiles=false' `
      --hiveconf 'hive.strict.checks.cartesian.product=false' `
      --hiveconf "dashboard_batch_id=$BatchId" --hiveconf "dashboard_model_version=$ModelVersion" -e "$Statement;" 2>&1)
    $Code=$LASTEXITCODE
    $AllOutput+=$Output
    $Output|ForEach-Object{Write-Host $_}
    if($Code -ne 0 -or ($Output -match '(?i)(FAILED:|^Error:)')){throw "$Stage statement $Number failed"}
    if($Output -match '(?m)^DUPLICATE_FOUND$'){throw "$Stage statement $Number found a duplicate primary key"}
  }
  if($Number -eq 0){throw "$Stage contains no executable statements"}
  if($Leaf -eq '09_validate_dashboard_dws_v2.sql'){
    $Required=@('category','store','verified_purchase','rating_matrix','confidence','monthly','alerts','samples','aspects','negative_reasons','source_join')
    foreach($Marker in $Required){if(-not($AllOutput -match "(?m)^$Marker\s")){throw "Hive validation marker missing: $Marker"}}
  }
}
function Test-ValidCategory{
  $Query="SELECT COUNT(*),COALESCE(SUM(review_count),0) FROM review_dw.dws_category_sentiment WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion'"
  $Output=@(& docker exec $HiveContainer beeline -u $Jdbc --silent=true --showHeader=false --outputformat=tsv2 --force=false -e "$Query;" 2>$null)
  return ($LASTEXITCODE -eq 0 -and ($Output -match '^1\s+99703$'))
}
function Get-HiveCounts{
  $Counts=[ordered]@{}
  foreach($Table in $AllTables){
    $Query="SELECT '$Table',COUNT(*) FROM review_dw.$Table WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';"
    $Output=@(& docker exec $HiveContainer beeline -u $Jdbc --silent=true --showHeader=false --outputformat=tsv2 --force=false -e $Query 2>&1)
    $Code=$LASTEXITCODE
    if($Code -ne 0 -or ($Output -match '(?i)(FAILED:|^Error:)')){$Output|ForEach-Object{Write-Host $_}; throw "Hive count failed for $Table"}
    foreach($Line in $Output){if($Line.ToString().Trim() -match "^$Table\s+(\d+)$"){$Counts[$Table]=[int64]$Matches[1]}}
    if(-not $Counts.Contains($Table)){throw "Missing Hive count for $Table"}
  }
  if($Counts.dws_sentiment_overview -ne 1 -or $Counts.dws_sentiment_daily -ne 4137 -or $Counts.dws_product_sentiment -ne 76784){throw 'Existing Hive DWS counts changed'}
  $Parent=Split-Path -Parent $HiveCountsPath; New-Item -ItemType Directory -Path $Parent -Force|Out-Null
  $Counts|ConvertTo-Json|Set-Content -LiteralPath $HiveCountsPath -Encoding utf8NoBOM
  return $Counts
}
function Export-HiveTables{
  foreach($Name in $ShortNames){
    $ContainerPath="/tmp/shopreview_dashboard_v2_export/$Name"
    & docker exec $HiveContainer rm -rf -- $ContainerPath; Assert-Exit "Clear exact container export $Name"
  }
  Invoke-HiveSql (Join-Path $RepoRoot 'sql\export\02_export_dashboard_dws_v2.sql') 'Hive v2 export'
  $Base=[IO.Path]::GetFullPath($ExportRoot).TrimEnd('\'); New-Item -ItemType Directory -Path $Base -Force|Out-Null
  foreach($Name in $ShortNames){
    $Target=[IO.Path]::GetFullPath((Join-Path $Base $Name))
    if(-not $Target.StartsWith($Base+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Unsafe export path: $Target"}
    if(Test-Path -LiteralPath $Target){Remove-Item -LiteralPath $Target -Recurse -Force}
    New-Item -ItemType Directory -Path $Target -Force|Out-Null
    & docker cp "${HiveContainer}:/tmp/shopreview_dashboard_v2_export/$Name/." $Target; Assert-Exit "Copy $Name export"
  }
}
function Invoke-MysqlSchema([string]$HostName,[int]$Port,[string]$User){
  $Client=(Get-Command mysql -ErrorAction Stop).Source; $Previous=$env:MYSQL_PWD
  try{$env:MYSQL_PWD=$env:SHOPREVIEW_MYSQL_PASSWORD; Get-Content -Raw (Join-Path $RepoRoot 'sql\mysql\03_extend_shopreview_serving_v2.sql')|& $Client "--host=$HostName" "--port=$Port" "--user=$User" '--default-character-set=utf8mb4'; Assert-Exit 'MySQL v2 schema'}finally{$env:MYSQL_PWD=$Previous}
}
function New-HandoffPackage{
  New-Item -ItemType Directory -Path $HandoffRoot -Force|Out-Null
  $Dump=Join-Path $HandoffRoot 'shopreview_serving_prod_v2.sql'; $Zip=Join-Path $HandoffRoot 'shopreview_serving_prod_v2.zip'; $HashFile=Join-Path $HandoffRoot 'shopreview_serving_prod_v2_sha256.txt'; $PackageManifest=Join-Path $HandoffRoot 'MYSQL_SERVING_V2_TABLE_MANIFEST.md'
  $TableArgs=$AllTables -join ' '
  $Command='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --quick --no-tablespaces --default-character-set=utf8mb4 --skip-triggers --set-gtid-purged=OFF shopreview_serving '+$TableArgs
  & docker exec $MysqlContainer sh -c $Command|Set-Content -LiteralPath $Dump -Encoding utf8NoBOM; Assert-Exit '13-table mysqldump'
  $ForbiddenLiterals=@('MYSQL_ROOT_PASSWORD','SHOPREVIEW_MYSQL_PASSWORD','user_id')
  foreach($Token in $ForbiddenLiterals){if(Select-String -LiteralPath $Dump -SimpleMatch $Token -Quiet){throw "Forbidden dump token detected: $Token"}}
  $ForbiddenSql='(?i)^\s*(CREATE\s+USER|GRANT)\b|DEFINER\s*=|IDENTIFIED\s+BY'
  if(Select-String -LiteralPath $Dump -Pattern $ForbiddenSql -Quiet){throw 'Forbidden account or privilege SQL detected in dump'}
  Copy-Item -LiteralPath $ManifestPath -Destination $PackageManifest -Force
  if(Test-Path -LiteralPath $Zip){Remove-Item -LiteralPath $Zip -Force}
  Compress-Archive -LiteralPath $Dump,$PackageManifest -DestinationPath $Zip
  $Hash=(Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
  $HashLines=@("SHA256=$Hash","file=shopreview_serving_prod_v2.zip","batch=$BatchId","model_version=$ModelVersion","generated_at_utc=$([DateTime]::UtcNow.ToString('o'))")
  foreach($Table in $AllTables){$HashLines+="$Table=$($HiveCounts.$Table)"}
  $HashLines|Set-Content -LiteralPath $HashFile -Encoding ascii
  $Entries=@(Add-Type -AssemblyName System.IO.Compression.FileSystem -PassThru|Out-Null; [IO.Compression.ZipFile]::OpenRead($Zip).Entries.Name)
  if($Entries.Count -ne 2 -or $Entries -notcontains 'shopreview_serving_prod_v2.sql' -or $Entries -notcontains 'MYSQL_SERVING_V2_TABLE_MANIFEST.md'){throw 'Unexpected ZIP contents'}
  Write-Host "Package=$Zip SHA256=$Hash"
}

try{
  Write-Host '[1/9] Branch and parameter safety'
  $Branch=(& git -C $RepoRoot symbolic-ref --short HEAD).Trim(); Assert-Exit 'Git branch check'
  if($Branch -ne 'data-dev'){throw "Required branch is data-dev; current branch is $Branch"}
  if($BatchId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$' -or $ModelVersion -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'){throw 'Unsafe batch/model parameter'}
  $script:ResumeIndex=0
  if($ResumeFromTable){
    $script:ResumeIndex=[array]::IndexOf($BuildTables,$ResumeFromTable)
    if($script:ResumeIndex -lt 0){throw "Unknown ResumeFromTable: $ResumeFromTable"}
    Write-Host "ResumeFromTable=$ResumeFromTable"
  }
  if($ValidateOnly -and ($BuildHive -or $SyncMysql)){throw 'ValidateOnly cannot be combined with Hive or MySQL write modes'}
  if($Package -and -not($SyncMysql -or $ValidateOnly)){throw 'Package requires a synchronized or validate-only reconciliation run'}
  if($PackageOnly -and ($BuildHive -or $SyncMysql -or $ValidateOnly -or $Package)){throw 'PackageOnly cannot be combined with other execution modes'}

  Write-Host '[2/9] Docker, Hive and MySQL health'
  & docker inspect -f '{{.State.Running}}' $HiveContainer $MysqlContainer; Assert-Exit 'Container health check'
  if($PackageOnly){
    if(-not(Test-Path -LiteralPath $HiveCountsPath) -or -not(Test-Path -LiteralPath $SummaryPath) -or -not(Test-Path -LiteralPath $ManifestPath)){throw 'PackageOnly requires validated counts, summary and manifest'}
    $HiveCounts=Get-Content -LiteralPath $HiveCountsPath -Raw|ConvertFrom-Json
    $Summary=Get-Content -LiteralPath $SummaryPath -Raw|ConvertFrom-Json
    if($Summary.result -ne 'PASS' -or $Summary.batch_id -ne $BatchId -or $Summary.model_version -ne $ModelVersion){throw 'PackageOnly summary scope is not reconciled'}
    foreach($Table in $AllTables){if($null -eq $HiveCounts.$Table -or [int64]$HiveCounts.$Table -ne [int64]$Summary.mysql_counts.$Table){throw "PackageOnly count mismatch: $Table"}}
    New-HandoffPackage
    Write-Host 'MYSQL V2 PACKAGE RESULT: PASS'
    exit 0
  }
  Write-Host '[3/9] Synthetic unit tests'
  if(-not $SkipTests){Push-Location $RepoRoot; try{Invoke-Python @('-m','unittest','tests.data.test_dashboard_dws_v2','-v')}finally{Pop-Location}}

  Write-Host '[4/9] Build exact Hive partitions'
  if($BuildHive){
    $script:PreserveValidCategory=Test-ValidCategory
    if($script:PreserveValidCategory){Write-Host 'PreserveValidCategory=YES'}
    Invoke-HiveSql (Join-Path $RepoRoot 'sql\dws\03_create_dashboard_dws_v2.sql') 'Hive DWS v2 build'
  }else{Write-Host 'BuildHive=NO'}
  Write-Host '[5/9] Hive aggregate validation'
  Invoke-HiveSql (Join-Path $RepoRoot 'sql\validation\09_validate_dashboard_dws_v2.sql') 'Hive DWS v2 validation'
  $HiveCounts=Get-HiveCounts

  $ResolvedEnv=if([IO.Path]::IsPathRooted($EnvFile)){$EnvFile}else{Join-Path $RepoRoot $EnvFile}; Import-SafeEnv $ResolvedEnv
  $HostName=if($env:SHOPREVIEW_MYSQL_HOST){$env:SHOPREVIEW_MYSQL_HOST}else{'127.0.0.1'}; $Port=if($env:SHOPREVIEW_MYSQL_PORT){[int]$env:SHOPREVIEW_MYSQL_PORT}else{3306}; $User=$env:SHOPREVIEW_MYSQL_USER
  if($env:SHOPREVIEW_MYSQL_DATABASE -and $env:SHOPREVIEW_MYSQL_DATABASE -ne 'shopreview_serving'){throw 'Database must be shopreview_serving'}
  if(-not $User -or -not $env:SHOPREVIEW_MYSQL_PASSWORD){throw 'MySQL writer configuration is incomplete'}

  Write-Host '[6/9] Controlled export and local validation'
  if($SyncMysql){Export-HiveTables; Invoke-MysqlSchema $HostName $Port $User}elseif(-not(Test-Path $ExportRoot)){throw 'ValidateOnly requires existing ignored exports'}
  Write-Host '[7/9] Transactional MySQL synchronization and 13-table reconciliation'
  $SyncArgs=@('-m','src.data.sync_dashboard_dws_v2_to_mysql','--export-root',$ExportRoot,'--batch-id',$BatchId,'--model-version',$ModelVersion,'--host',$HostName,'--port',[string]$Port,'--user',$User,'--password-env','SHOPREVIEW_MYSQL_PASSWORD','--summary-path',$SummaryPath,'--manifest-path',$ManifestPath,'--hive-counts-path',$HiveCountsPath)
  if($ValidateOnly){$SyncArgs+='--validate-only'}
  Push-Location $RepoRoot; try{Invoke-Python $SyncArgs}finally{Pop-Location}

  Write-Host '[8/9] Safe handoff package'
  if($Package){New-HandoffPackage}else{Write-Host 'Package=NO'}
  Write-Host '[9/9] Result'
  Write-Host 'DWS V2 BUILD RESULT: PASS'
  Write-Host 'MYSQL 13-TABLE SYNC RESULT: PASS'
  Write-Host 'HIVE MYSQL RECONCILIATION RESULT: PASS'
  Write-Host 'MYSQL V2 PACKAGE RESULT: PASS'
  exit 0
}catch{
  Write-Error $_
  Write-Host 'DWS V2 BUILD RESULT: FAIL'
  Write-Host 'MYSQL 13-TABLE SYNC RESULT: FAIL'
  Write-Host 'HIVE MYSQL RECONCILIATION RESULT: FAIL'
  Write-Host 'MYSQL V2 PACKAGE RESULT: FAIL'
  exit 1
}
