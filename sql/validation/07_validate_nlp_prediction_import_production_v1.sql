USE review_dw;

SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;

SELECT COUNT(*) AS staging_row_count
FROM stg_nlp_predictions
WHERE load_batch_id='${hiveconf:prediction_batch_id}';

SELECT COUNT(*) AS valid_staging_row_count
FROM stg_nlp_predictions
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND review_key IS NOT NULL AND TRIM(review_key)<>''
  AND pred_label IN ('negative','neutral','positive')
  AND pred_score BETWEEN 0.0 AND 1.0
  AND (negative_score IS NULL OR negative_score BETWEEN 0.0 AND 1.0)
  AND (neutral_score IS NULL OR neutral_score BETWEEN 0.0 AND 1.0)
  AND (positive_score IS NULL OR positive_score BETWEEN 0.0 AND 1.0)
  AND model_version='${hiveconf:prediction_model_version}'
  AND inferred_at IS NOT NULL;

SELECT COUNT(*) AS production_sentiment_row_count
FROM dwd_review_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version_partition='${hiveconf:model_version_partition}'
  AND model_version='${hiveconf:prediction_model_version}';

SELECT COUNT(*) AS duplicate_staging_prediction_key_groups
FROM (
  SELECT review_key,model_version
  FROM stg_nlp_predictions
  WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  GROUP BY review_key,model_version HAVING COUNT(*)>1
) duplicate_keys;

SELECT COUNT(*) AS duplicate_production_prediction_key_groups
FROM (
  SELECT review_key,model_version
  FROM dwd_review_sentiment
  WHERE load_batch_id='${hiveconf:prediction_batch_id}'
    AND model_version_partition='${hiveconf:model_version_partition}'
  GROUP BY review_key,model_version HAVING COUNT(*)>1
) duplicate_keys;

SELECT COUNT(*) AS unknown_review_key_count
FROM stg_nlp_predictions p
LEFT JOIN dwd_amazon_fashion_review d
  ON p.review_key=d.review_key AND d.load_batch_id='prod_v1_100k'
WHERE p.load_batch_id='${hiveconf:prediction_batch_id}'
  AND p.model_version='${hiveconf:prediction_model_version}'
  AND d.review_key IS NULL;

SELECT COUNT(*) AS missing_review_key_count
FROM dwd_amazon_fashion_review d
LEFT JOIN dwd_review_sentiment p
  ON d.review_key=p.review_key
 AND d.load_batch_id=p.load_batch_id
 AND p.model_version='${hiveconf:prediction_model_version}'
 AND p.model_version_partition='${hiveconf:model_version_partition}'
WHERE d.load_batch_id='prod_v1_100k'
  AND p.review_key IS NULL;

SELECT
  CASE WHEN COUNT(d.review_key)=0 THEN 0.0
       ELSE CAST(COUNT(p.review_key) AS DOUBLE)/COUNT(d.review_key) END AS prediction_coverage
FROM dwd_amazon_fashion_review d
LEFT JOIN dwd_review_sentiment p
  ON d.review_key=p.review_key
 AND d.load_batch_id=p.load_batch_id
 AND p.model_version='${hiveconf:prediction_model_version}'
 AND p.model_version_partition='${hiveconf:model_version_partition}'
WHERE d.load_batch_id='prod_v1_100k';

SELECT COUNT(*) AS invalid_label_count
FROM stg_nlp_predictions
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND (pred_label IS NULL OR pred_label NOT IN ('negative','neutral','positive'));

SELECT COUNT(*) AS invalid_score_count
FROM stg_nlp_predictions
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND (pred_score IS NULL OR pred_score<0 OR pred_score>1
    OR (negative_score IS NOT NULL AND (negative_score<0 OR negative_score>1))
    OR (neutral_score IS NOT NULL AND (neutral_score<0 OR neutral_score>1))
    OR (positive_score IS NOT NULL AND (positive_score<0 OR positive_score>1)));

SELECT COUNT(*) AS blank_model_version_count
FROM stg_nlp_predictions
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND (model_version IS NULL OR TRIM(model_version)='');

SELECT COUNT(*) AS joined_view_row_count
FROM vw_dwd_review_with_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}';

SELECT pred_label,COUNT(*) AS row_count
FROM dwd_review_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version_partition='${hiveconf:model_version_partition}'
GROUP BY pred_label ORDER BY pred_label;

SELECT model_version,COUNT(*) AS row_count
FROM dwd_review_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
GROUP BY model_version ORDER BY model_version;

SELECT COUNT(*) AS invalid_inferred_timestamp_count
FROM stg_nlp_predictions
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND inferred_at IS NULL;
