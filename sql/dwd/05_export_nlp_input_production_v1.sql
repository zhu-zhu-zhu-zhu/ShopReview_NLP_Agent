USE review_dw;

-- Hive 2.3.2 CombineHiveInputFormat can fail while projecting this partitioned
-- Parquet table. Scope the compatible reader to this export session only.
SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;
SET hive.merge.mapfiles=false;
SET hive.merge.mapredfiles=false;
SET hive.merge.tezfiles=false;

DROP TABLE IF EXISTS review_dw.tmp_nlp_input_prod_v1_100k;

CREATE TABLE review_dw.tmp_nlp_input_prod_v1_100k (
  review_key STRING,
  review_text_clean STRING,
  rating_label STRING,
  rating DOUBLE,
  parent_asin STRING,
  main_category STRING,
  review_time TIMESTAMP,
  load_batch_id STRING
)
STORED AS PARQUET;

INSERT OVERWRITE TABLE review_dw.tmp_nlp_input_prod_v1_100k
SELECT
  review_key,
  review_text_clean,
  rating_label,
  rating,
  parent_asin,
  main_category,
  review_time,
  load_batch_id
FROM review_dw.dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
  AND review_text_clean IS NOT NULL
  AND TRIM(review_text_clean)<>''
  AND review_key IS NOT NULL
  AND TRIM(review_key)<>''
  AND rating_label IN ('negative','neutral','positive');
