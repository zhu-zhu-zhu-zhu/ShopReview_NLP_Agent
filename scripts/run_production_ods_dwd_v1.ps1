param(
  [string]$ReviewPath='D:\bdt-app-course\projects\ecommerce_review_sentiment\data\raw\amazon_fashion\Amazon_Fashion.jsonl',
  [string]$MetaPath='D:\bdt-app-course\projects\ecommerce_review_sentiment\data\raw\amazon_fashion\meta_Amazon_Fashion.jsonl',
  [int]$ReviewLimit=100000,
  [string]$BatchId='prod_v1_100k',
  [switch]$ValidateOnly
)

$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$NameNode='tier4_stu_namenode'
$HiveServer='tier4_stu_hiveserver2'
$Jdbc='jdbc:hive2://localhost:10000/default'
$OutputDir=Join-Path $RepoRoot 'data\processed\production_v1'
$ReviewOutput=Join-Path $OutputDir 'ods_amazon_fashion_review_prod_v1.txt'
$MetaOutput=Join-Path $OutputDir 'ods_amazon_fashion_meta_prod_v1.txt'
$SummaryPath=Join-Path $OutputDir 'production_v1_summary.json'
$ReviewHdfs="/data/review_dw/ods/amazon_fashion_review/load_batch_id=$BatchId"
$MetaHdfs="/data/review_dw/ods/amazon_fashion_meta/load_batch_id=$BatchId"

function Assert-Exit([string]$Stage){
  if($LASTEXITCODE -ne 0){throw "$Stage failed with exit code $LASTEXITCODE"}
}

function Get-LineCount([string]$Path){
  [int64]$Count=0
  foreach($Line in [System.IO.File]::ReadLines($Path)){[void]$Line;$Count++}
  return $Count
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

function Hive-Metrics([string]$Query){
  $Metrics=@{}
  foreach($Line in @(Hive-Lines $Query)){
    $Parts=$Line -split "`t",2
    if($Parts.Count -ne 2 -or $Parts[1] -notmatch '^\d+$'){throw "Invalid Hive metric row: $Line"}
    $Metrics[$Parts[0]]=[int64]$Parts[1]
  }
  return $Metrics
}

function Run-Sql([string]$LocalPath,[string]$RemotePath){
  docker cp $LocalPath "${HiveServer}:$RemotePath"|Out-Host;Assert-Exit 'SQL docker copy'
  docker exec $HiveServer beeline -u $Jdbc --silent=true -f $RemotePath|Out-Host;Assert-Exit "Hive SQL $RemotePath"
}

function Invoke-Validation{
  Write-Host '[validation] Running aggregate validation SQL'
  Run-Sql 'sql\validation\05_validate_production_ods_dwd_v1.sql' '/tmp/05_validate_production_ods_dwd_v1.sql'
  $Metrics=Hive-Metrics @'
USE review_dw;
SELECT 'ods_review',COUNT(*) FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';
SELECT 'ods_meta',COUNT(*) FROM ods_amazon_fashion_meta WHERE load_batch_id='prod_v1_100k';
SELECT 'eligible_raw',COUNT(*) FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>'';
SELECT 'eligible_unique',COUNT(DISTINCT sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|', coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|', coalesce(title,''), '|#|', coalesce(review_text,'')),256)) FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>'';
SELECT 'source_duplicate_groups',COUNT(*) FROM (SELECT sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|', coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|', coalesce(title,''), '|#|', coalesce(review_text,'')),256) AS review_key FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>'' GROUP BY sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|', coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|', coalesce(title,''), '|#|', coalesce(review_text,'')),256) HAVING COUNT(*)>1) x;
SELECT 'source_duplicate_excess',SUM(row_count-1) FROM (SELECT COUNT(*) AS row_count FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>'' GROUP BY sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|', coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|', coalesce(title,''), '|#|', coalesce(review_text,'')),256) HAVING COUNT(*)>1) x;
SELECT 'empty_ods',COUNT(*) FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (review_text IS NULL OR trim(review_text)='');
SELECT 'dwd',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';
SELECT 'null_key',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (review_key IS NULL OR trim(review_key)='');
SELECT 'duplicate_key_groups',COUNT(*) FROM (SELECT review_key FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' GROUP BY review_key HAVING COUNT(*)>1) x;
SELECT 'blank_clean',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (review_text_clean IS NULL OR trim(review_text_clean)='');
SELECT 'invalid_labels',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND rating_label NOT IN ('negative','neutral','positive');
SELECT 'valid_timestamp',COUNT(review_time) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';
SELECT 'invalid_timestamp',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (review_time IS NULL OR dt IS NULL OR review_year IS NULL);
SELECT 'metadata_matched',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND metadata_matched=true;
SELECT 'metadata_unmatched',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND metadata_matched=false;
SELECT 'negative',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND rating_label='negative';
SELECT 'neutral',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND rating_label='neutral';
SELECT 'positive',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND rating_label='positive';
SELECT 'invalid_ods_values',COUNT(*) FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (rating IS NULL OR rating<1 OR rating>5 OR helpful_vote IS NULL OR helpful_vote<0 OR verified_purchase IS NULL);
SELECT 'invalid_dwd_values',COUNT(*) FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND (text_length IS NULL OR text_length<=0 OR metadata_matched IS NULL);
SELECT 'partition_count',COUNT(*) FROM (SELECT review_year FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' GROUP BY review_year) p;
'@
  if($Metrics['ods_review'] -ne 100000){throw "ODS review count is $($Metrics['ods_review']); expected 100000"}
  if($Metrics['dwd'] -ne $Metrics['eligible_unique']){throw "DWD deduplicated reconciliation failed: dwd=$($Metrics['dwd']) unique_eligible=$($Metrics['eligible_unique'])"}
  if(($Metrics['eligible_raw']-$Metrics['source_duplicate_excess']) -ne $Metrics['dwd']){throw 'ODS eligible-to-DWD duplicate reconciliation failed'}
  foreach($Name in @('null_key','duplicate_key_groups','blank_clean','invalid_labels','invalid_timestamp','invalid_ods_values','invalid_dwd_values')){
    if($Metrics[$Name] -ne 0){throw "Production quality invariant failed: $Name=$($Metrics[$Name])"}
  }
  if($Metrics['partition_count'] -le 0){throw 'No production DWD partitions found'}
  if(($Metrics['metadata_matched']+$Metrics['metadata_unmatched']) -ne $Metrics['dwd']){throw 'Metadata distribution does not reconcile to DWD'}
  if(($Metrics['negative']+$Metrics['neutral']+$Metrics['positive']) -ne $Metrics['dwd']){throw 'Weak-label distribution does not reconcile to DWD'}
  return $Metrics
}

try{
  Push-Location $RepoRoot
  try{
    Write-Host '[1/10] Branch and parameter validation'
    $Branch=git symbolic-ref --short HEAD;Assert-Exit 'Git branch check'
    if($Branch -ne 'data-dev'){throw 'Current branch must be data-dev'}
    if($BatchId -ne 'prod_v1_100k'){throw 'This production-v1 runner only permits batch prod_v1_100k'}

    Write-Host '[2/10] Docker, HDFS and Hive health'
    docker version|Out-Null;Assert-Exit 'Docker'
    docker exec $NameNode hdfs dfs -ls /|Out-Null;Assert-Exit 'HDFS'
    docker exec $HiveServer beeline -u $Jdbc -e 'USE review_dw; SHOW TABLES;'|Out-Null;Assert-Exit 'Hive'

    if($ValidateOnly){
      Write-Host '[3/3] ValidateOnly: no local generation, upload or table writes'
      $Metrics=Invoke-Validation
      Write-Host "ODS=$($Metrics['ods_review'])/$($Metrics['ods_meta']) DWD=$($Metrics['dwd'])"
    }else{
      Write-Host '[3/10] Raw source validation and synthetic unit tests'
      if(-not(Test-Path -LiteralPath $ReviewPath -PathType Leaf)){throw "Review source missing: $ReviewPath"}
      if(-not(Test-Path -LiteralPath $MetaPath -PathType Leaf)){throw "Metadata source missing: $MetaPath"}
      python -m unittest tests.data.test_prepare_production_ods_dwd_v1 -v;Assert-Exit 'Unit tests'

      Write-Host '[4/10] Streaming production-v1 preparation'
      python -m src.data.prepare_production_ods_dwd_v1 --review-path $ReviewPath --meta-path $MetaPath --output-dir $OutputDir --review-limit $ReviewLimit --batch-id $BatchId --progress-every 100000
      Assert-Exit 'Production-v1 preparation'
      $Summary=Get-Content -Raw -LiteralPath $SummaryPath|ConvertFrom-Json
      if($Summary.batch_id -ne $BatchId -or $Summary.valid_reviews_selected -ne $ReviewLimit){throw 'Preparation summary identity mismatch'}

      Write-Host '[5/10] Local generated-row reconciliation'
      $ReviewRows=Get-LineCount $ReviewOutput
      $MetaRows=Get-LineCount $MetaOutput
      if($ReviewRows -ne $Summary.generated_review_file_rows -or $MetaRows -ne $Summary.generated_metadata_file_rows){throw 'Local generated row counts do not match summary'}
      if($ReviewRows -ne 100000){throw "Production-v1 requires exactly 100000 review rows; got $ReviewRows"}
      Write-Host "Local rows: reviews=$ReviewRows metadata=$MetaRows missing_parent_asin=$($Summary.missing_metadata_parent_asin_count)"

      Write-Host '[6/10] Exact production-v1 HDFS batch upload'
      docker exec $NameNode hdfs dfs -mkdir -p $ReviewHdfs $MetaHdfs;Assert-Exit 'HDFS batch directory creation'
      docker cp $ReviewOutput "${NameNode}:/tmp/ods_amazon_fashion_review_prod_v1.txt";Assert-Exit 'Review docker copy'
      docker cp $MetaOutput "${NameNode}:/tmp/ods_amazon_fashion_meta_prod_v1.txt";Assert-Exit 'Metadata docker copy'
      docker exec $NameNode hdfs dfs -put -f '/tmp/ods_amazon_fashion_review_prod_v1.txt' "$ReviewHdfs/ods_amazon_fashion_review_prod_v1.txt";Assert-Exit 'Review HDFS upload'
      docker exec $NameNode hdfs dfs -put -f '/tmp/ods_amazon_fashion_meta_prod_v1.txt' "$MetaHdfs/ods_amazon_fashion_meta_prod_v1.txt";Assert-Exit 'Metadata HDFS upload'

      Write-Host '[7/10] Partitioned production ODS tables'
      Run-Sql 'sql\ods\03_create_amazon_fashion_ods_production_v1.sql' '/tmp/03_create_amazon_fashion_ods_production_v1.sql'

      Write-Host '[8/10] Partitioned production DWD Parquet table'
      Run-Sql 'sql\dwd\04_create_amazon_fashion_dwd_production_v1.sql' '/tmp/04_create_amazon_fashion_dwd_production_v1.sql'

      Write-Host '[9/10] Production ODS/DWD validation'
      $Metrics=Invoke-Validation
      if($Metrics['ods_meta'] -ne $MetaRows){throw "ODS metadata mismatch: hive=$($Metrics['ods_meta']) local=$MetaRows"}

      Write-Host '[10/10] Final measured counts'
      Write-Host "ODS=$($Metrics['ods_review'])/$($Metrics['ods_meta']) DWD=$($Metrics['dwd']) filtered=$($Metrics['empty_ods']) matched=$($Metrics['metadata_matched']) unmatched=$($Metrics['metadata_unmatched'])"
    }
  }finally{Pop-Location}
  Write-Host 'PRODUCTION ODS/DWD V1 RUNNER: PASS';exit 0
}catch{
  Write-Error $_
  Write-Host 'PRODUCTION ODS/DWD V1 RUNNER: FAIL';exit 1
}
