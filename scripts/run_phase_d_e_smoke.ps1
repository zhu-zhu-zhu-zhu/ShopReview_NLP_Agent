param(
  [string]$ReviewPath = 'D:\bdt-app-course\projects\ecommerce_review_sentiment\data\raw\amazon_fashion\Amazon_Fashion.jsonl',
  [string]$MetaPath = 'D:\bdt-app-course\projects\ecommerce_review_sentiment\data\raw\amazon_fashion\meta_Amazon_Fashion.jsonl'
)

$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$OutDir=Join-Path $RepoRoot 'data\processed\phase_d_e_smoke'
$NameNode='tier4_stu_namenode'; $HiveServer='tier4_stu_hiveserver2'
$Jdbc='jdbc:hive2://localhost:10000/default'
$ReviewHdfs='/data/review_dw/smoke_d/ods_review_matched'
$MetaHdfs='/data/review_dw/smoke_d/ods_meta_matched'

function Assert-Exit([string]$Stage){if($LASTEXITCODE -ne 0){throw "$Stage failed: $LASTEXITCODE"}}
function Hive-Scalar([string]$Query){
  $Old=$ErrorActionPreference
  try{$ErrorActionPreference='Continue';$O=@(& docker exec $HiveServer beeline --silent=true --showHeader=false --outputformat=tsv2 -u $Jdbc -e $Query 2>$null);$Code=$LASTEXITCODE}
  finally{$ErrorActionPreference=$Old}
  if($Code -ne 0){throw "Hive scalar failed: $Query"}
  $N=@($O|ForEach-Object{$_.ToString().Trim()}|Where-Object{$_ -match '^\d+$'})
  if(-not $N.Count){throw "No numeric Hive result: $Query"}; return [int64]$N[-1]
}
function Run-Sql([string]$Local,[string]$Remote){
  docker cp $Local "${HiveServer}:$Remote"; Assert-Exit 'SQL docker copy'
  docker exec $HiveServer beeline -u $Jdbc -f $Remote; Assert-Exit "Hive SQL $Remote"
}

try{
  Push-Location $RepoRoot
  try{
    Write-Host '[1/10] Branch and raw-file validation'
    $Branch=git symbolic-ref --short HEAD; Assert-Exit 'Git branch check'
    if($Branch -ne 'data-dev'){throw 'Current branch must be data-dev'}
    if(-not(Test-Path -LiteralPath $ReviewPath -PathType Leaf)){throw 'Review raw file missing'}
    if(-not(Test-Path -LiteralPath $MetaPath -PathType Leaf)){throw 'Metadata raw file missing'}

    Write-Host '[2/10] Docker, HDFS and Hive health'
    docker version|Out-Null; Assert-Exit 'Docker'
    docker exec $NameNode hdfs dfs -ls /|Out-Null; Assert-Exit 'HDFS'
    docker exec $HiveServer beeline -u $Jdbc -e 'SHOW DATABASES;'|Out-Null; Assert-Exit 'Hive'

    Write-Host '[3/10] Bounded coordinated sample preparation'
    python -m src.data.prepare_phase_d_e_smoke --review-path $ReviewPath --meta-path $MetaPath --output-dir $OutDir
    Assert-Exit 'Preparation'
    $S=Get-Content -Raw -LiteralPath (Join-Path $OutDir 'preparation_summary.json')|ConvertFrom-Json
    if($S.matched_pair_count -lt 20){throw 'Fewer than 20 matched pairs'}
    if($S.converted_review_rows -ne $S.converted_metadata_rows){throw 'Converted counts differ'}
    Write-Host "Pairs=$($S.matched_pair_count) NLP rows=$($S.dwd_eligible_nlp_rows)"

    Write-Host '[4/10] Uploading only Phase D coordinated files'
    docker exec $NameNode hdfs dfs -mkdir -p $ReviewHdfs $MetaHdfs; Assert-Exit 'HDFS mkdir'
    docker cp (Join-Path $OutDir 'ods_review_matched.txt') "${NameNode}:/tmp/ods_review_matched.txt"; Assert-Exit 'Review copy'
    docker cp (Join-Path $OutDir 'ods_meta_matched.txt') "${NameNode}:/tmp/ods_meta_matched.txt"; Assert-Exit 'Meta copy'
    docker exec $NameNode hdfs dfs -put -f '/tmp/ods_review_matched.txt' $ReviewHdfs; Assert-Exit 'Review put'
    docker exec $NameNode hdfs dfs -put -f '/tmp/ods_meta_matched.txt' $MetaHdfs; Assert-Exit 'Meta put'

    Write-Host '[5/10] Matched ODS tables'
    Run-Sql 'sql\ods\02_create_amazon_fashion_matched_smoke.sql' '/tmp/02_create_amazon_fashion_matched_smoke.sql'
    $Or=Hive-Scalar 'SELECT COUNT(*) FROM review_dw.ods_amazon_fashion_review_matched_smoke;'
    $Om=Hive-Scalar 'SELECT COUNT(*) FROM review_dw.ods_amazon_fashion_meta_matched_smoke;'
    if($Or -ne $S.matched_pair_count -or $Om -ne $S.matched_pair_count){throw "ODS mismatch $Or/$Om"}

    Write-Host '[6/10] DWD smoke build'
    Run-Sql 'sql\dwd\01_create_amazon_fashion_dwd_smoke.sql' '/tmp/01_create_amazon_fashion_dwd_smoke.sql'
    $Dwd=Hive-Scalar 'SELECT COUNT(*) FROM review_dw.dwd_amazon_fashion_review_smoke;'
    if($Dwd -ne $S.dwd_eligible_nlp_rows){throw "DWD/NLP count mismatch $Dwd/$($S.dwd_eligible_nlp_rows)"}

    Write-Host '[7/10] Phase D validation'
    Run-Sql 'sql\validation\02_validate_phase_d_smoke.sql' '/tmp/02_validate_phase_d_smoke.sql'
    $Eligible=Hive-Scalar "SELECT COUNT(*) FROM review_dw.ods_amazon_fashion_review_matched_smoke r JOIN review_dw.ods_amazon_fashion_meta_matched_smoke m ON r.parent_asin=m.parent_asin WHERE r.review_text IS NOT NULL AND trim(r.review_text)<>'';"
    if($Dwd -ne $Eligible){throw "DWD reconciliation failed: dwd=$Dwd eligible=$Eligible"}
    foreach($Q in @(
      "SELECT COUNT(*) FROM review_dw.dwd_amazon_fashion_review_smoke WHERE review_key IS NULL OR trim(review_key)='';",
      'SELECT COUNT(*) FROM (SELECT review_key FROM review_dw.dwd_amazon_fashion_review_smoke GROUP BY review_key HAVING COUNT(*)>1) x;',
      "SELECT COUNT(*) FROM review_dw.dwd_amazon_fashion_review_smoke WHERE review_text_clean IS NULL OR trim(review_text_clean)='';",
      "SELECT COUNT(*) FROM review_dw.dwd_amazon_fashion_review_smoke WHERE rating_label NOT IN ('negative','neutral','positive');"
    )){if((Hive-Scalar $Q)-ne 0){throw "Phase D invariant failed: $Q"}}

    Write-Host '[8/10] Synthetic prediction contract build (not a model)'
    Run-Sql 'sql\dwd\02_create_sentiment_contract_smoke.sql' '/tmp/02_create_sentiment_contract_smoke.sql'

    Write-Host '[9/10] Phase E contract validation'
    Run-Sql 'sql\validation\03_validate_phase_e_contract_smoke.sql' '/tmp/03_validate_phase_e_contract_smoke.sql'
    $Pred=Hive-Scalar 'SELECT COUNT(*) FROM review_dw.dwd_review_sentiment_contract_smoke;'
    $View=Hive-Scalar 'SELECT COUNT(*) FROM review_dw.vw_dwd_review_with_sentiment_smoke;'
    if($Pred -ne $Dwd -or $View -ne $Dwd){throw 'Prediction reconciliation failed'}
    foreach($Q in @(
      'SELECT COUNT(*) FROM review_dw.vw_dwd_review_with_sentiment_smoke WHERE pred_label IS NULL;',
      'SELECT COUNT(*) FROM review_dw.dwd_review_sentiment_contract_smoke p LEFT JOIN review_dw.dwd_amazon_fashion_review_smoke d ON p.review_key=d.review_key WHERE d.review_key IS NULL;',
      'SELECT COUNT(*) FROM (SELECT review_key,model_version FROM review_dw.dwd_review_sentiment_contract_smoke GROUP BY review_key,model_version HAVING COUNT(*)>1) x;',
      "SELECT COUNT(*) FROM review_dw.dwd_review_sentiment_contract_smoke WHERE pred_label NOT IN ('negative','neutral','positive');",
      'SELECT COUNT(*) FROM review_dw.dwd_review_sentiment_contract_smoke WHERE pred_score<0 OR pred_score>1 OR pred_score IS NULL;',
      "SELECT COUNT(*) FROM review_dw.dwd_review_sentiment_contract_smoke WHERE model_version IS NULL OR trim(model_version)='';"
    )){if((Hive-Scalar $Q)-ne 0){throw "Phase E invariant failed: $Q"}}

    Write-Host '[10/10] Final counts'
    Write-Host "ODS=$Or/$Om DWD=$Dwd Prediction=$Pred View=$View"
  }finally{Pop-Location}
  Write-Host 'PHASE D/E SMOKE RUNNER: PASS';exit 0
}catch{Write-Error $_;Write-Host 'PHASE D/E SMOKE RUNNER: FAIL';exit 1}
