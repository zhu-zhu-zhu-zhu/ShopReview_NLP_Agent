$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$HiveServer='tier4_stu_hiveserver2'
$NameNode='tier4_stu_namenode'
$Jdbc='jdbc:hive2://localhost:10000/default'
$Fixture=Join-Path $RepoRoot 'tests\fixtures\aspect_results_contract_smoke.json'
$ProcessedDir=Join-Path $RepoRoot 'data\processed\phase_f_smoke'
$AspectText=Join-Path $ProcessedDir 'dwd_review_aspect_contract_smoke.txt'
$ExportDir=Join-Path $RepoRoot 'exports\agent\smoke'

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

function Hive-Metrics([string]$Query){
  $Metrics=@{}
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
  docker cp $LocalPath "${HiveServer}:$RemotePath";Assert-Exit 'SQL docker copy'
  docker exec $HiveServer beeline -u $Jdbc --silent=true -f $RemotePath;Assert-Exit "Hive SQL $RemotePath"
}

try{
  Push-Location $RepoRoot
  try{
    Write-Host '[1/9] Branch and service validation'
    $Branch=git symbolic-ref --short HEAD;Assert-Exit 'Git branch check'
    if($Branch -ne 'data-dev'){throw 'Current branch must be data-dev'}
    docker version|Out-Null;Assert-Exit 'Docker'
    docker exec $NameNode hdfs dfs -ls /|Out-Null;Assert-Exit 'HDFS'
    docker exec $HiveServer beeline -u $Jdbc -e 'USE review_dw; SHOW TABLES;'|Out-Null;Assert-Exit 'Hive'

    Write-Host '[2/9] Required Phase D/E table validation'
    foreach($Table in @('dwd_amazon_fashion_review_smoke','dwd_review_sentiment_contract_smoke','vw_dwd_review_with_sentiment_smoke')){Assert-Table $Table}

    Write-Host '[3/9] Synthetic aspect fixture preparation (not an LLM result)'
    python -m src.data.prepare_phase_f_aspect_smoke --fixture $Fixture --output $AspectText
    Assert-Exit 'Aspect fixture preparation'
    $FixtureData=Get-Content -Raw -LiteralPath $Fixture|ConvertFrom-Json
    $FixtureRows=$FixtureData.Count
    if($FixtureRows -lt 10 -or $FixtureRows -gt 100){throw "Unexpected fixture row count: $FixtureRows"}

    Write-Host '[4/9] Aspect contract smoke table load'
    docker cp $AspectText "${HiveServer}:/tmp/dwd_review_aspect_contract_smoke.txt";Assert-Exit 'Aspect text docker copy'
    docker cp 'sql\dwd\03_create_aspect_contract_smoke.sql' "${HiveServer}:/tmp/03_create_aspect_contract_smoke.sql";Assert-Exit 'Aspect SQL docker copy'
    docker exec $HiveServer beeline -u $Jdbc --silent=true --hiveconf 'phase_f_aspect_input=/tmp/dwd_review_aspect_contract_smoke.txt' -f '/tmp/03_create_aspect_contract_smoke.sql'
    Assert-Exit 'Aspect contract Hive load'
    $AspectMetrics=Hive-Metrics @'
USE review_dw;
SELECT 'aspect_rows',COUNT(*) FROM dwd_review_aspect_contract_smoke;
SELECT 'unknown_keys',COUNT(*) FROM dwd_review_aspect_contract_smoke a LEFT JOIN dwd_amazon_fashion_review_smoke d ON a.review_key=d.review_key WHERE d.review_key IS NULL;
SELECT 'duplicate_keys',COUNT(*) FROM (SELECT review_key,aspect,reason_code,extractor_version FROM dwd_review_aspect_contract_smoke GROUP BY review_key,aspect,reason_code,extractor_version HAVING COUNT(*)>1) x;
SELECT 'invalid_aspects',COUNT(*) FROM dwd_review_aspect_contract_smoke WHERE aspect NOT IN ('size','color','material','comfort','workmanship','description_mismatch','packaging','delivery','price','other');
SELECT 'invalid_labels',COUNT(*) FROM dwd_review_aspect_contract_smoke WHERE aspect_sentiment NOT IN ('negative','neutral','positive');
SELECT 'invalid_confidence',COUNT(*) FROM dwd_review_aspect_contract_smoke WHERE confidence IS NULL OR confidence<0 OR confidence>1;
'@
    $AspectRows=$AspectMetrics['aspect_rows']
    if($AspectRows -ne $FixtureRows){throw "Aspect row reconciliation failed: fixture=$FixtureRows hive=$AspectRows"}
    foreach($Name in @('unknown_keys','duplicate_keys','invalid_aspects','invalid_labels','invalid_confidence')){
      if($AspectMetrics[$Name] -ne 0){throw "Aspect contract invariant failed: $Name=$($AspectMetrics[$Name])"}
    }

    Write-Host '[5/9] Four Phase F DWS smoke tables'
    Run-Sql 'sql\dws\01_create_phase_f_dws_smoke.sql' '/tmp/01_create_phase_f_dws_smoke.sql'

    Write-Host '[6/9] Phase F validation SQL'
    Run-Sql 'sql\validation\04_validate_phase_f_dws_smoke.sql' '/tmp/04_validate_phase_f_dws_smoke.sql'
    $Metrics=Hive-Metrics @'
USE review_dw;
SELECT 'dwd_rows',COUNT(*) FROM dwd_amazon_fashion_review_smoke;
SELECT 'sentiment_rows',COUNT(*) FROM dwd_review_sentiment_contract_smoke;
SELECT 'view_rows',COUNT(*) FROM vw_dwd_review_with_sentiment_smoke;
SELECT 'overview_rows',COUNT(*) FROM dws_sentiment_overview_smoke;
SELECT 'overview_review_count',review_count FROM dws_sentiment_overview_smoke;
SELECT 'overview_sentiment_sum',positive_count+neutral_count+negative_count FROM dws_sentiment_overview_smoke;
SELECT 'product_rows',COUNT(*) FROM dws_product_sentiment_smoke;
SELECT 'product_review_sum',SUM(review_count) FROM dws_product_sentiment_smoke;
SELECT 'aspect_summary_rows',COUNT(*) FROM dws_aspect_summary_smoke;
SELECT 'aspect_mention_sum',SUM(mention_count) FROM dws_aspect_summary_smoke;
SELECT 'negative_aspect_rows',COUNT(*) FROM dwd_review_aspect_contract_smoke WHERE aspect_sentiment='negative';
SELECT 'negative_reason_rows',COUNT(*) FROM dws_negative_reason_smoke;
SELECT 'negative_reason_sum',SUM(reason_count) FROM dws_negative_reason_smoke;
SELECT 'invalid_overview_rates',COUNT(*) FROM dws_sentiment_overview_smoke WHERE positive_rate<0 OR positive_rate>1 OR neutral_rate<0 OR neutral_rate>1 OR negative_rate<0 OR negative_rate>1;
SELECT 'invalid_product_rates',COUNT(*) FROM dws_product_sentiment_smoke WHERE positive_rate<0 OR positive_rate>1 OR neutral_rate<0 OR neutral_rate>1 OR negative_rate<0 OR negative_rate>1 OR verified_purchase_rate<0 OR verified_purchase_rate>1;
SELECT 'invalid_reason_shares',COUNT(*) FROM dws_negative_reason_smoke WHERE reason_share<0 OR reason_share>1;
'@
    $DwdRows=$Metrics['dwd_rows'];$SentimentRows=$Metrics['sentiment_rows'];$ViewRows=$Metrics['view_rows']
    $OverviewRows=$Metrics['overview_rows'];$OverviewReviewCount=$Metrics['overview_review_count'];$OverviewSentimentSum=$Metrics['overview_sentiment_sum']
    $ProductRows=$Metrics['product_rows'];$ProductReviewSum=$Metrics['product_review_sum']
    $AspectSummaryRows=$Metrics['aspect_summary_rows'];$AspectMentionSum=$Metrics['aspect_mention_sum']
    $NegativeAspectRows=$Metrics['negative_aspect_rows'];$NegativeReasonRows=$Metrics['negative_reason_rows'];$NegativeReasonSum=$Metrics['negative_reason_sum']
    if($OverviewRows -ne 1 -or $OverviewReviewCount -ne $ViewRows -or $OverviewSentimentSum -ne $OverviewReviewCount){throw 'Sentiment overview reconciliation failed'}
    if($ProductReviewSum -ne $OverviewReviewCount){throw 'Product DWS reconciliation failed'}
    if($AspectMentionSum -ne $AspectRows){throw 'Aspect DWS reconciliation failed'}
    if($NegativeReasonSum -ne $NegativeAspectRows){throw 'Negative reason reconciliation failed'}
    foreach($Name in @('invalid_overview_rates','invalid_product_rates','invalid_reason_shares')){
      if($Metrics[$Name] -ne 0){throw "DWS rate invariant failed: $Name=$($Metrics[$Name])"}
    }

    Write-Host '[7/9] Safe aggregate JSON export for Agent mock adapter'
    python -m src.data.export_phase_f_agent_json --container $HiveServer --jdbc $Jdbc --output-dir $ExportDir
    Assert-Exit 'Agent JSON export'

    Write-Host '[8/9] Exported JSON validation'
    python -m src.data.export_phase_f_agent_json --output-dir $ExportDir --validate-only
    Assert-Exit 'Agent JSON validation'
    foreach($Name in @('sentiment_overview.json','product_sentiment.json','aspect_summary.json','negative_reasons.json','manifest.json')){
      if(-not(Test-Path -LiteralPath (Join-Path $ExportDir $Name) -PathType Leaf)){throw "Missing Agent export: $Name"}
    }

    Write-Host '[9/9] Final measured counts'
    Write-Host "DWD=$DwdRows SentimentContract=$SentimentRows AspectContract=$AspectRows Overview=$OverviewRows Products=$ProductRows AspectSummary=$AspectSummaryRows NegativeReasons=$NegativeReasonRows"
  }finally{Pop-Location}
  Write-Host 'PHASE F DWS SMOKE RUNNER: PASS';exit 0
}catch{
  Write-Error $_
  Write-Host 'PHASE F DWS SMOKE RUNNER: FAIL';exit 1
}
