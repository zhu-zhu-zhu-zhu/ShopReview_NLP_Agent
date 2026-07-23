USE review_dw;

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_mysql_export/overview'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'field.delim'='\001',
  'serialization.null.format'='\\N'
)
STORED AS TEXTFILE
SELECT
  load_batch_id,
  model_version,
  review_count,
  product_count,
  positive_count,
  neutral_count,
  negative_count,
  positive_rate,
  neutral_rate,
  negative_rate,
  average_rating,
  average_prediction_score,
  generated_at
FROM review_dw.dws_sentiment_overview
WHERE load_batch_id='${hiveconf:serving_batch_id}'
  AND model_version='${hiveconf:serving_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_mysql_export/daily'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'field.delim'='\001',
  'serialization.null.format'='\\N'
)
STORED AS TEXTFILE
SELECT
  dt,
  load_batch_id,
  model_version,
  review_count,
  positive_count,
  neutral_count,
  negative_count,
  positive_rate,
  neutral_rate,
  negative_rate,
  average_rating,
  generated_at
FROM review_dw.dws_sentiment_daily
WHERE load_batch_id='${hiveconf:serving_batch_id}'
  AND model_version='${hiveconf:serving_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_mysql_export/product'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'field.delim'='\001',
  'serialization.null.format'='\\N'
)
STORED AS TEXTFILE
SELECT
  parent_asin,
  product_title,
  store_name,
  main_category,
  load_batch_id,
  model_version,
  review_count,
  average_rating,
  positive_count,
  neutral_count,
  negative_count,
  positive_rate,
  neutral_rate,
  negative_rate,
  verified_purchase_rate,
  average_helpful_vote,
  average_prediction_score,
  generated_at
FROM review_dw.dws_product_sentiment
WHERE load_batch_id='${hiveconf:serving_batch_id}'
  AND model_version='${hiveconf:serving_model_version}';
