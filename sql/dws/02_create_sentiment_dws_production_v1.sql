USE review_dw;

SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;
SET hive.merge.mapfiles=false;
SET hive.merge.mapredfiles=false;
SET hive.merge.tezfiles=false;

CREATE TABLE IF NOT EXISTS review_dw.dws_sentiment_overview (
  review_count BIGINT,
  product_count BIGINT,
  positive_count BIGINT,
  neutral_count BIGINT,
  negative_count BIGINT,
  positive_rate DOUBLE,
  neutral_rate DOUBLE,
  negative_rate DOUBLE,
  average_rating DOUBLE,
  average_prediction_score DOUBLE,
  generated_at TIMESTAMP
)
PARTITIONED BY (load_batch_id STRING, model_version STRING)
STORED AS PARQUET;

INSERT OVERWRITE TABLE review_dw.dws_sentiment_overview
PARTITION (
  load_batch_id='${hiveconf:prediction_batch_id}',
  model_version='${hiveconf:prediction_model_version}'
)
SELECT
  COUNT(*),
  COUNT(DISTINCT parent_asin),
  SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
  SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
  SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  AVG(rating),
  AVG(pred_score),
  current_timestamp
FROM review_dw.vw_dwd_review_with_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}';

CREATE TABLE IF NOT EXISTS review_dw.dws_sentiment_daily (
  dt STRING,
  review_count BIGINT,
  positive_count BIGINT,
  neutral_count BIGINT,
  negative_count BIGINT,
  positive_rate DOUBLE,
  neutral_rate DOUBLE,
  negative_rate DOUBLE,
  average_rating DOUBLE,
  generated_at TIMESTAMP
)
PARTITIONED BY (load_batch_id STRING, model_version STRING)
STORED AS PARQUET;

INSERT OVERWRITE TABLE review_dw.dws_sentiment_daily
PARTITION (
  load_batch_id='${hiveconf:prediction_batch_id}',
  model_version='${hiveconf:prediction_model_version}'
)
SELECT
  dt,
  COUNT(*),
  SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
  SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
  SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  AVG(rating),
  current_timestamp
FROM review_dw.vw_dwd_review_with_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}'
GROUP BY dt;

CREATE TABLE IF NOT EXISTS review_dw.dws_product_sentiment (
  parent_asin STRING,
  product_title STRING,
  store_name STRING,
  main_category STRING,
  review_count BIGINT,
  average_rating DOUBLE,
  positive_count BIGINT,
  neutral_count BIGINT,
  negative_count BIGINT,
  positive_rate DOUBLE,
  neutral_rate DOUBLE,
  negative_rate DOUBLE,
  verified_purchase_rate DOUBLE,
  average_helpful_vote DOUBLE,
  average_prediction_score DOUBLE,
  generated_at TIMESTAMP
)
PARTITIONED BY (load_batch_id STRING, model_version STRING)
STORED AS PARQUET;

INSERT OVERWRITE TABLE review_dw.dws_product_sentiment
PARTITION (
  load_batch_id='${hiveconf:prediction_batch_id}',
  model_version='${hiveconf:prediction_model_version}'
)
SELECT
  parent_asin,
  product_title,
  store_name,
  main_category,
  COUNT(*),
  AVG(rating),
  SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
  SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
  SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN verified_purchase THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  AVG(CAST(helpful_vote AS DOUBLE)),
  AVG(pred_score),
  current_timestamp
FROM review_dw.vw_dwd_review_with_sentiment
WHERE load_batch_id='${hiveconf:prediction_batch_id}'
  AND model_version='${hiveconf:prediction_model_version}'
  AND parent_asin IS NOT NULL
  AND TRIM(parent_asin)<>''
GROUP BY parent_asin, product_title, store_name, main_category;
