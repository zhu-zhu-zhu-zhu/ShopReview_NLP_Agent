param(
  [string]$BatchId='prod_v1_100k',
  [string]$OutputPath='data\processed\nlp_production_v1\nlp_input_prod_v1.jsonl',
  [switch]$ValidateOnly
)

$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$HiveServer='tier4_stu_hiveserver2'
$Jdbc='jdbc:hive2://localhost:10000/default'
$ExpectedDwdRows=99703
$SummaryPath=Join-Path $RepoRoot 'reports\nlp_handoff\nlp_input_prod_v1_summary.json'
$ManifestPath=Join-Path $RepoRoot 'reports\nlp_handoff\nlp_input_prod_v1_manifest.json'
if(-not [System.IO.Path]::IsPathRooted($OutputPath)){$OutputPath=Join-Path $RepoRoot $OutputPath}

function Assert-Exit([string]$Stage){
  if($LASTEXITCODE -ne 0){throw "$Stage failed with exit code $LASTEXITCODE"}
}

function Hive-Lines([string]$Query){
  $OldPreference=$ErrorActionPreference
  try{
    $ErrorActionPreference='Continue'
    $Output=@(& docker exec $HiveServer beeline -u $Jdbc --silent=true --showHeader=false --outputformat=tsv2 -e $Query 2>$null)
    $Code=$LASTEXITCODE
  }finally{$ErrorActionPreference=$OldPreference}
  if($Code -ne 0){throw "Hive query failed: $Query"}
  return @($Output|ForEach-Object{$_.ToString().Trim()}|Where-Object{$_})
}

function Hive-Scalar([string]$Query){
  $Lines=@(Hive-Lines $Query)
  $Numbers=@($Lines|Where-Object{$_ -match '^\d+$'})
  if(-not $Numbers.Count){throw "Hive query returned no integer scalar: $Query"}
  return [int64]$Numbers[-1]
}

function Hive-Metrics{
  $Metrics=@{}
  $Query=@'
USE review_dw;
SELECT 'dwd_rows',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';
SELECT 'eligible_rows',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND review_text_clean IS NOT NULL AND trim(review_text_clean)<>'' AND review_key IS NOT NULL AND trim(review_key)<>'' AND rating_label IN ('negative','neutral','positive');
SELECT 'null_keys',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (review_key IS NULL OR trim(review_key)='');
SELECT 'duplicate_key_groups',COUNT(*) FROM (SELECT review_key FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' GROUP BY review_key HAVING COUNT(*)>1) x;
SELECT 'blank_text',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (review_text_clean IS NULL OR trim(review_text_clean)='');
SELECT 'invalid_labels',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (rating_label IS NULL OR rating_label NOT IN ('negative','neutral','positive'));
SELECT 'negative',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND rating_label='negative';
SELECT 'neutral',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND rating_label='neutral';
SELECT 'positive',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND rating_label='positive';
SELECT 'with_parent_asin',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND parent_asin IS NOT NULL AND trim(parent_asin)<>'';
SELECT 'with_main_category',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND main_category IS NOT NULL AND trim(main_category)<>'';
SELECT 'with_review_time',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND review_time IS NOT NULL;
SELECT 'export_rows',COUNT(*) FROM tmp_nlp_input_prod_v1_100k;
SELECT 'invalid_export_batch',COUNT(*) FROM tmp_nlp_input_prod_v1_100k WHERE load_batch_id IS NULL OR load_batch_id<>'prod_v1_100k';
'@
  foreach($Line in @(Hive-Lines $Query)){
    $Parts=$Line -split "`t",2
    if($Parts.Count -ne 2 -or $Parts[1] -notmatch '^\d+$'){throw "Invalid Hive metric row: $Line"}
    $Metrics[$Parts[0]]=[int64]$Parts[1]
  }
  return $Metrics
}

function Assert-Table([string]$Name){
  $Lines=@(Hive-Lines "SHOW TABLES IN review_dw LIKE '$Name';")
  if($Lines -notcontains $Name){throw "Required Hive table is missing: review_dw.$Name"}
}

function Run-Sql([string]$LocalPath,[string]$RemotePath){
  docker cp $LocalPath "${HiveServer}:$RemotePath"|Out-Host;Assert-Exit 'SQL docker copy'
  docker exec $HiveServer beeline -u $Jdbc --silent=true -f $RemotePath|Out-Host;Assert-Exit "Hive SQL $RemotePath"
}

function Assert-ExportSchema{
  $Actual=@(Hive-Lines 'SHOW COLUMNS IN review_dw.tmp_nlp_input_prod_v1_100k;')
  $Expected=@('review_key','review_text_clean','rating_label','rating','parent_asin','main_category','review_time','load_batch_id')
  if(($Actual -join ',') -ne ($Expected -join ',')){throw "Unexpected export table schema: $($Actual -join ',')"}
  if($Actual -contains 'user_id'){throw 'Export table must not contain user_id'}
}

function Assert-HiveMetrics([hashtable]$Metrics){
  if($Metrics['dwd_rows'] -ne $ExpectedDwdRows){throw "Production DWD count is $($Metrics['dwd_rows']); expected $ExpectedDwdRows"}
  if($Metrics['eligible_rows'] -ne $Metrics['dwd_rows']){throw 'Eligible DWD rows do not reconcile to production DWD'}
  if($Metrics['export_rows'] -ne $Metrics['eligible_rows']){throw 'Hive export table does not reconcile to eligible DWD rows'}
  foreach($Name in @('null_keys','duplicate_key_groups','blank_text','invalid_labels','invalid_export_batch')){
    if($Metrics[$Name] -ne 0){throw "NLP handoff invariant failed: $Name=$($Metrics[$Name])"}
  }
  if(($Metrics['negative']+$Metrics['neutral']+$Metrics['positive']) -ne $Metrics['eligible_rows']){throw 'Weak-label distribution does not reconcile'}
}

try{
  Push-Location $RepoRoot
  try{
    Write-Host '[1/8] Branch and parameter validation'
    $Branch=git symbolic-ref --short HEAD;Assert-Exit 'Git branch check'
    if($Branch -ne 'data-dev'){throw 'Current branch must be data-dev'}
    if($BatchId -ne 'prod_v1_100k'){throw 'This runner only permits batch prod_v1_100k'}

    Write-Host '[2/8] Docker, Hive and production DWD validation'
    docker version|Out-Null;Assert-Exit 'Docker'
    Assert-Table 'dwd_amazon_fashion_review'
    $DwdRows=Hive-Scalar "SELECT COUNT(*) FROM review_dw.dwd_amazon_fashion_review WHERE load_batch_id='$BatchId';"
    if($DwdRows -ne $ExpectedDwdRows){throw "Production DWD count is $DwdRows; expected $ExpectedDwdRows"}

    if($ValidateOnly){
      Write-Host '[3/6] ValidateOnly: verify existing Hive export table without writes'
      Assert-Table 'tmp_nlp_input_prod_v1_100k'
      Assert-ExportSchema
    }else{
      Write-Host '[3/8] Synthetic unit tests'
      python -m unittest tests.data.test_export_nlp_input_production_v1 -v;Assert-Exit 'Unit tests'

      Write-Host '[4/8] Repeatable isolated Hive export table'
      Run-Sql 'sql\dwd\05_export_nlp_input_production_v1.sql' '/tmp/05_export_nlp_input_production_v1.sql'
      Assert-Table 'tmp_nlp_input_prod_v1_100k'
      Assert-ExportSchema

      Write-Host '[5/8] Atomic UTF-8 JSONL export and tracked safe artifacts'
      python -m src.data.export_nlp_input_production_v1 --container $HiveServer --jdbc $Jdbc --batch-id $BatchId --output-path $OutputPath --summary-path $SummaryPath --manifest-path $ManifestPath
      Assert-Exit 'Production NLP input export'
    }

    Write-Host "[$(if($ValidateOnly){'4/6'}else{'6/8'})] Hive reconciliation and validation SQL"
    $Metrics=Hive-Metrics
    Assert-HiveMetrics $Metrics
    Run-Sql 'sql\validation\06_validate_nlp_handoff_production_v1.sql' '/tmp/06_validate_nlp_handoff_production_v1.sql'

    Write-Host "[$(if($ValidateOnly){'5/6'}else{'7/8'})] Local JSONL, summary, manifest and SHA-256 validation"
    python -m src.data.export_nlp_input_production_v1 --batch-id $BatchId --output-path $OutputPath --summary-path $SummaryPath --manifest-path $ManifestPath --expected-row-count $Metrics['eligible_rows'] --validate-only
    Assert-Exit 'Local NLP handoff validation'

    Write-Host "[$(if($ValidateOnly){'6/6'}else{'8/8'})] Final measured counts"
    $Summary=Get-Content -Raw -LiteralPath $SummaryPath|ConvertFrom-Json
    Write-Host "DWD=$($Metrics['dwd_rows']) Eligible=$($Metrics['eligible_rows']) Export=$($Summary.export_row_count) UniqueKeys=$($Summary.unique_review_key_count) Labels=$($Summary.negative_count)/$($Summary.neutral_count)/$($Summary.positive_count)"
  }finally{Pop-Location}
  Write-Host 'NLP PRODUCTION HANDOFF RUNNER: PASS';exit 0
}catch{
  Write-Error $_
  Write-Host 'NLP PRODUCTION HANDOFF RUNNER: FAIL';exit 1
}
