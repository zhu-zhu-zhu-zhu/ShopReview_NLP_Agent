USE review_dw;

SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;

SELECT COUNT(*) AS overview_rows_for_model
FROM dws_sentiment_overview
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}';

SELECT COUNT(*) AS duplicate_overview_model_groups
FROM (
  SELECT load_batch_id,model_version
  FROM dws_sentiment_overview
  GROUP BY load_batch_id,model_version HAVING COUNT(*)>1
) duplicate_models;

SELECT review_count,
       positive_count+neutral_count+negative_count AS label_count_sum
FROM dws_sentiment_overview
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}';

SELECT o.review_count AS overview_count,p.prediction_count
FROM dws_sentiment_overview o
JOIN (
  SELECT load_batch_id,model_version,COUNT(*) AS prediction_count
  FROM dwd_review_sentiment
  WHERE load_batch_id='${hiveconf:prediction_batch_id}'
    AND model_version='${hiveconf:prediction_model_version}'
  GROUP BY load_batch_id,model_version
) p ON o.load_batch_id=p.load_batch_id AND o.model_version=p.model_version
WHERE o.load_batch_id='${hiveconf:prediction_batch_id}'
  AND o.model_version='${hiveconf:prediction_model_version}';

SELECT SUM(review_count) AS daily_review_count_sum
FROM dws_sentiment_daily
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}';

SELECT SUM(review_count) AS product_review_count_sum
FROM dws_product_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}';

SELECT COUNT(*) AS invalid_overview_rate_rows
FROM dws_sentiment_overview
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}'
  AND (positive_rate<0 OR positive_rate>1 OR neutral_rate<0 OR neutral_rate>1 OR negative_rate<0 OR negative_rate>1);

SELECT COUNT(*) AS invalid_daily_rate_rows
FROM dws_sentiment_daily
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}'
  AND (positive_rate<0 OR positive_rate>1 OR neutral_rate<0 OR neutral_rate>1 OR negative_rate<0 OR negative_rate>1);

SELECT COUNT(*) AS invalid_product_rate_rows
FROM dws_product_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}'
  AND (positive_rate<0 OR positive_rate>1 OR neutral_rate<0 OR neutral_rate>1 OR negative_rate<0 OR negative_rate>1
    OR verified_purchase_rate<0 OR verified_purchase_rate>1);

SELECT COUNT(*) AS blank_product_parent_asin_rows
FROM dws_product_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}'
  AND (parent_asin IS NULL OR TRIM(parent_asin)='');

SELECT COUNT(*) AS unexpected_model_version_rows
FROM dws_sentiment_overview
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version<>'${hiveconf:prediction_model_version}';

SELECT COUNT(*) AS smoke_or_synthetic_source_rows
FROM dwd_review_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND (LOWER(model_version) LIKE '%smoke%'
    OR LOWER(model_version) LIKE '%synthetic%'
    OR LOWER(model_version) LIKE '%contract%not%a%model%');
