param(
  [string]$PredictionPath='',
  [string]$ModelVersion='',
  [string]$BatchId='prod_v1_100k',
  [double]$MinimumCoverage=1.0,
  [switch]$PrepareOnly,
  [switch]$ValidateOnly,
  [switch]$BuildDws,
  [switch]$ForceSameVersion
)

$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$HiveServer='tier4_stu_hiveserver2'
$NameNode='tier4_stu_namenode'
$Jdbc='jdbc:hive2://localhost:10000/default'
$ExpectedDwdRows=99703
$ManifestPath=Join-Path $RepoRoot 'reports\nlp_handoff\nlp_input_prod_v1_manifest.json'
$ProcessedDir=Join-Path $RepoRoot 'data\processed\nlp_predictions_production_v1'
$ValidationSummary=Join-Path $ProcessedDir 'prediction_validation_summary.json'
$PreparedText=Join-Path $ProcessedDir 'nlp_predictions_prepared.txt'
$ConversionSummary=Join-Path $ProcessedDir 'conversion_summary.json'
$PreparedSqlFiles=@(
  'sql\dwd\06_create_nlp_prediction_tables_production_v1.sql',
  'sql\dwd\07_import_nlp_predictions_production_v1.sql',
  'sql\dwd\08_create_dwd_sentiment_view_production_v1.sql',
  'sql\dws\02_create_sentiment_dws_production_v1.sql',
  'sql\validation\07_validate_nlp_prediction_import_production_v1.sql',
  'sql\validation\08_validate_sentiment_dws_production_v1.sql'
)

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

function Test-HiveTable([string]$Name){
  $Lines=@(Hive-Lines "SHOW TABLES IN review_dw LIKE '$Name';")
  return $Lines -contains $Name
}

function Get-OptionalTableCount([string]$Name){
  if(-not(Test-HiveTable $Name)){return [int64]-1}
  return Hive-Scalar "SELECT COUNT(*) FROM review_dw.$Name;"
}

function Get-ProductionSnapshot{
  $Snapshot=@{}
  foreach($Name in @('stg_nlp_predictions','dwd_review_sentiment','dws_sentiment_overview','dws_sentiment_daily','dws_product_sentiment')){
    $Snapshot[$Name]=Get-OptionalTableCount $Name
  }
  return $Snapshot
}

function Assert-SameSnapshot([hashtable]$Before,[hashtable]$After){
  foreach($Name in $Before.Keys){
    if($Before[$Name] -ne $After[$Name]){throw "PrepareOnly changed Hive object ${Name}: $($Before[$Name]) -> $($After[$Name])"}
  }
}

function Get-ModelPartition([string]$Version){
  if($Version -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'){throw 'ModelVersion contains unsafe characters'}
  $Normalized=[regex]::Replace($Version.ToLower(),'[^a-z0-9_-]+','_').Trim('_')
  if(-not $Normalized){$Normalized='model'}
  if($Normalized.Length -gt 80){$Normalized=$Normalized.Substring(0,80)}
  $Sha=[System.Security.Cryptography.SHA256]::Create()
  try{$HashBytes=$Sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Version))}finally{$Sha.Dispose()}
  $Hash=([System.BitConverter]::ToString($HashBytes)).Replace('-','').ToLower().Substring(0,12)
  return "${Normalized}_$Hash"
}

function Run-Sql([string]$LocalPath,[string]$RemotePath,[hashtable]$HiveConf=@{}){
  docker cp $LocalPath "${HiveServer}:$RemotePath"|Out-Host;Assert-Exit 'SQL docker copy'
  $Arguments=@('exec',$HiveServer,'beeline','-u',$Jdbc,'--silent=true')
  foreach($Name in @($HiveConf.Keys|Sort-Object)){$Arguments+=@('--hiveconf',"$Name=$($HiveConf[$Name])")}
  $Arguments+=@('-f',$RemotePath)
  & docker @Arguments|Out-Host;Assert-Exit "Hive SQL $RemotePath"
}

function Run-HiveStatement([string]$Query){
  docker exec $HiveServer beeline -u $Jdbc --silent=true -e $Query|Out-Host;Assert-Exit 'Hive statement'
}

function Assert-PredictionImport([string]$SafePartition,[int64]$ExpectedRows){
  $ProductionRows=Hive-Scalar "SELECT COUNT(*) FROM review_dw.dwd_review_sentiment WHERE load_batch_id='$BatchId' AND model_version_partition='$SafePartition' AND model_version='$ModelVersion';"
  $ViewRows=Hive-Scalar "SELECT COUNT(*) FROM review_dw.vw_dwd_review_with_sentiment WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';"
  if($ProductionRows -ne $ExpectedRows -or $ViewRows -ne $ExpectedRows){throw "Prediction reconciliation failed: expected=$ExpectedRows production=$ProductionRows view=$ViewRows"}
  foreach($Query in @(
    "SELECT COUNT(*) FROM (SELECT review_key,model_version FROM review_dw.dwd_review_sentiment WHERE load_batch_id='$BatchId' AND model_version_partition='$SafePartition' GROUP BY review_key,model_version HAVING COUNT(*)>1) x;",
    "SELECT COUNT(*) FROM review_dw.dwd_review_sentiment WHERE load_batch_id='$BatchId' AND model_version_partition='$SafePartition' AND (pred_label NOT IN ('negative','neutral','positive') OR pred_score<0 OR pred_score>1 OR inferred_at IS NULL);"
  )){if((Hive-Scalar $Query)-ne 0){throw "Imported prediction invariant failed: $Query"}}
  return $ProductionRows
}

function Assert-Dws([int64]$PredictionRows){
  $OverviewRows=Hive-Scalar "SELECT COUNT(*) FROM review_dw.dws_sentiment_overview WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';"
  $OverviewCount=Hive-Scalar "SELECT review_count FROM review_dw.dws_sentiment_overview WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';"
  $DailySum=Hive-Scalar "SELECT SUM(review_count) FROM review_dw.dws_sentiment_daily WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';"
  $ProductSum=Hive-Scalar "SELECT SUM(review_count) FROM review_dw.dws_product_sentiment WHERE load_batch_id='$BatchId' AND model_version='$ModelVersion';"
  if($OverviewRows -ne 1 -or $OverviewCount -ne $PredictionRows -or $DailySum -ne $OverviewCount -or $ProductSum -ne $OverviewCount){throw 'Production DWS reconciliation failed'}
}

try{
  Push-Location $RepoRoot
  try{
    Write-Host '[1/7] Branch and parameter safety'
    $Branch=git symbolic-ref --short HEAD;Assert-Exit 'Git branch check'
    if($Branch -ne 'data-dev'){throw 'Current branch must be data-dev'}
    if($BatchId -ne 'prod_v1_100k'){throw 'This runner only permits batch prod_v1_100k'}
    if($MinimumCoverage -lt 0 -or $MinimumCoverage -gt 1){throw 'MinimumCoverage must be between 0 and 1'}
    if($PrepareOnly -and ($ValidateOnly -or $BuildDws -or $ForceSameVersion)){throw 'PrepareOnly cannot be combined with import switches'}
    if($ValidateOnly -and ($BuildDws -or $ForceSameVersion)){throw 'ValidateOnly cannot build or replace data'}

    Write-Host '[2/7] Docker, Hive and production DWD health'
    docker version|Out-Null;Assert-Exit 'Docker'
    $DwdRows=Hive-Scalar "SELECT COUNT(*) FROM review_dw.dwd_amazon_fashion_review WHERE load_batch_id='$BatchId';"
    if($DwdRows -ne $ExpectedDwdRows){throw "Production DWD count is $DwdRows; expected $ExpectedDwdRows"}

    if($PrepareOnly){
      Write-Host '[3/5] Snapshot production prediction and DWS objects (read-only)'
      $Before=Get-ProductionSnapshot

      Write-Host '[4/5] Synthetic unit tests and prepared-file checks'
      python -m py_compile src\data\validate_nlp_predictions_production_v1.py src\data\prepare_nlp_predictions_for_hive.py;Assert-Exit 'Python syntax check'
      python -m unittest tests.data.test_validate_nlp_predictions_production_v1 -v;Assert-Exit 'Synthetic unit tests'
      foreach($File in $PreparedSqlFiles){if(-not(Test-Path -LiteralPath $File -PathType Leaf)){throw "Missing prepared SQL: $File"}}
      foreach($File in @('src\data\validate_nlp_predictions_production_v1.py','src\data\prepare_nlp_predictions_for_hive.py','tests\data\test_validate_nlp_predictions_production_v1.py')){
        if(-not(Test-Path -LiteralPath $File -PathType Leaf)){throw "Missing prepared code: $File"}
      }

      Write-Host '[5/5] Confirm no Hive prediction or DWS mutation'
      $After=Get-ProductionSnapshot
      Assert-SameSnapshot $Before $After
      foreach($Name in @($After.Keys|Sort-Object)){
        $State=if($After[$Name] -eq -1){'ABSENT'}else{"UNCHANGED rows=$($After[$Name])"}
        Write-Host "$Name=$State"
      }
      Write-Host "ProductionDWD=$DwdRows RealPredictionFileRequired=NO HiveWrites=NO"
      Write-Host 'NLP PREDICTION IMPORT PREPARATION: PASS';exit 0
    }

    if(-not $ModelVersion){throw 'ModelVersion is required outside PrepareOnly'}
    $SafePartition=Get-ModelPartition $ModelVersion
    $HiveConf=@{
      prediction_batch_id=$BatchId
      prediction_model_version=$ModelVersion
      model_version_partition=$SafePartition
    }

    if($ValidateOnly){
      Write-Host '[3/4] Validate existing production prediction version without writes'
      foreach($Table in @('stg_nlp_predictions','dwd_review_sentiment')){if(-not(Test-HiveTable $Table)){throw "Required Hive table is missing: $Table"}}
      if(-not(Test-HiveTable 'vw_dwd_review_with_sentiment')){throw 'Required joined view is missing'}
      Run-Sql 'sql\validation\07_validate_nlp_prediction_import_production_v1.sql' '/tmp/07_validate_nlp_prediction_import_production_v1.sql' $HiveConf
      $Rows=Assert-PredictionImport $SafePartition (Hive-Scalar "SELECT COUNT(*) FROM review_dw.dwd_review_sentiment WHERE load_batch_id='$BatchId' AND model_version_partition='$SafePartition';")
      Write-Host '[4/4] Existing version validation complete'
      Write-Host "ModelVersion=$ModelVersion PredictionRows=$Rows"
      Write-Host 'NLP PREDICTION IMPORT VALIDATION: PASS';exit 0
    }

    if(-not $PredictionPath -or -not(Test-Path -LiteralPath $PredictionPath -PathType Leaf)){throw 'A real PredictionPath is required for import'}
    $PredictionPath=(Resolve-Path -LiteralPath $PredictionPath).Path

    Write-Host '[3/7] Strict streaming prediction validation'
    $ValidatorArgs=@(
      '-m','src.data.validate_nlp_predictions_production_v1',
      '--prediction-path',$PredictionPath,'--manifest-path',$ManifestPath,
      '--output-summary',$ValidationSummary,'--expected-batch-id',$BatchId,
      '--expected-model-version',$ModelVersion,'--minimum-coverage',$MinimumCoverage
    )
    if($MinimumCoverage -lt 1.0){$ValidatorArgs+='--allow-partial'}
    & python @ValidatorArgs;Assert-Exit 'Prediction validation'
    $Validation=Get-Content -Raw -LiteralPath $ValidationSummary|ConvertFrom-Json
    if($Validation.validation_status -ne 'PASS' -or $Validation.model_version_partition -ne $SafePartition){throw 'Prediction validation summary is invalid'}

    Write-Host '[4/7] Atomic Hive text conversion'
    python -m src.data.prepare_nlp_predictions_for_hive --prediction-path $PredictionPath --output-path $PreparedText --output-summary $ConversionSummary --batch-id $BatchId --expected-model-version $ModelVersion
    Assert-Exit 'Hive prediction preparation'
    $Conversion=Get-Content -Raw -LiteralPath $ConversionSummary|ConvertFrom-Json
    if($Conversion.converted_row_count -ne $Validation.valid_prediction_row_count){throw 'Validation/conversion row count mismatch'}

    Write-Host '[5/7] Exact HDFS staging partition and Hive schemas'
    Run-Sql 'sql\dwd\06_create_nlp_prediction_tables_production_v1.sql' '/tmp/06_create_nlp_prediction_tables_production_v1.sql'
    $ExistingRows=Hive-Scalar "SELECT COUNT(*) FROM review_dw.dwd_review_sentiment WHERE load_batch_id='$BatchId' AND model_version_partition='$SafePartition';"
    if($ExistingRows -gt 0 -and -not $ForceSameVersion){throw 'This exact batch/model partition already exists; rerun with -ForceSameVersion only after explicit confirmation'}
    $HdfsPath="/data/review_dw/staging/nlp_predictions/load_batch_id=$BatchId/model_version_partition=$SafePartition"
    $ContainerFile="/tmp/nlp_predictions_$SafePartition.txt"
    docker exec $NameNode hdfs dfs -mkdir -p $HdfsPath;Assert-Exit 'HDFS staging directory creation'
    docker cp $PreparedText "${NameNode}:$ContainerFile";Assert-Exit 'Prediction docker copy'
    docker exec $NameNode hdfs dfs -put -f $ContainerFile "$HdfsPath/nlp_predictions_prepared.txt";Assert-Exit 'Prediction HDFS upload'
    Run-HiveStatement "USE review_dw; ALTER TABLE stg_nlp_predictions ADD IF NOT EXISTS PARTITION (load_batch_id='$BatchId') LOCATION '$HdfsPath'; ALTER TABLE stg_nlp_predictions PARTITION (load_batch_id='$BatchId') SET LOCATION '$HdfsPath';"

    Write-Host '[6/7] Version-isolated prediction import and joined view'
    Run-Sql 'sql\dwd\07_import_nlp_predictions_production_v1.sql' '/tmp/07_import_nlp_predictions_production_v1.sql' $HiveConf
    Run-Sql 'sql\dwd\08_create_dwd_sentiment_view_production_v1.sql' '/tmp/08_create_dwd_sentiment_view_production_v1.sql'
    Run-Sql 'sql\validation\07_validate_nlp_prediction_import_production_v1.sql' '/tmp/07_validate_nlp_prediction_import_production_v1.sql' $HiveConf
    $PredictionRows=Assert-PredictionImport $SafePartition ([int64]$Validation.valid_prediction_row_count)

    Write-Host '[7/7] Optional production DWS build'
    if($BuildDws){
      Run-Sql 'sql\dws\02_create_sentiment_dws_production_v1.sql' '/tmp/02_create_sentiment_dws_production_v1.sql' $HiveConf
      Run-Sql 'sql\validation\08_validate_sentiment_dws_production_v1.sql' '/tmp/08_validate_sentiment_dws_production_v1.sql' $HiveConf
      Assert-Dws $PredictionRows
      Write-Host "Production DWS built for $BatchId / $ModelVersion"
    }else{Write-Host 'BuildDws not supplied: production DWS was not populated'}
    Write-Host "ImportedRows=$PredictionRows ModelVersion=$ModelVersion Partition=$SafePartition"
  }finally{Pop-Location}
  Write-Host 'NLP PREDICTION IMPORT RUNNER: PASS';exit 0
}catch{
  Write-Error $_
  Write-Host 'NLP PREDICTION IMPORT RUNNER: FAIL';exit 1
}
