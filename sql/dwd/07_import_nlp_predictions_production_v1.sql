USE review_dw;

SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;
SET hive.merge.mapfiles=false;
SET hive.merge.mapredfiles=false;
SET hive.merge.tezfiles=false;

-- This overwrites only the explicitly selected batch/model partition. The runner
-- requires -ForceSameVersion before rerunning an existing exact partition.
INSERT OVERWRITE TABLE review_dw.dwd_review_sentiment
PARTITION (
  load_batch_id='${hiveconf:prediction_batch_id}',
  model_version_partition='${hiveconf:model_version_partition}'
)
SELECT
  s.review_key,
  s.pred_label,
  s.pred_score,
  s.negative_score,
  s.neutral_score,
  s.positive_score,
  s.model_version,
  s.inferred_at,
  current_timestamp
FROM review_dw.stg_nlp_predictions s
JOIN review_dw.dwd_amazon_fashion_review d
  ON s.review_key=d.review_key
 AND s.load_batch_id=d.load_batch_id
WHERE s.load_batch_id='${hiveconf:prediction_batch_id}'
  AND d.load_batch_id='prod_v1_100k'
  AND s.review_key IS NOT NULL
  AND TRIM(s.review_key)<>''
  AND s.pred_label IN ('negative','neutral','positive')
  AND s.pred_score BETWEEN 0.0 AND 1.0
  AND (s.negative_score IS NULL OR s.negative_score BETWEEN 0.0 AND 1.0)
  AND (s.neutral_score IS NULL OR s.neutral_score BETWEEN 0.0 AND 1.0)
  AND (s.positive_score IS NULL OR s.positive_score BETWEEN 0.0 AND 1.0)
  AND s.model_version='${hiveconf:prediction_model_version}'
  AND TRIM(s.model_version)<>''
  AND s.inferred_at IS NOT NULL;
