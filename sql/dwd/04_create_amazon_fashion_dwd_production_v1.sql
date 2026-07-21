CREATE DATABASE IF NOT EXISTS review_dw;

CREATE TABLE IF NOT EXISTS review_dw.dwd_amazon_fashion_review (
  review_key STRING,
  asin STRING,
  parent_asin STRING,
  user_id STRING,
  rating DOUBLE,
  title STRING,
  review_text STRING,
  review_text_clean STRING,
  review_timestamp BIGINT,
  review_time TIMESTAMP,
  dt STRING,
  helpful_vote BIGINT,
  verified_purchase BOOLEAN,
  product_title STRING,
  store_name STRING,
  main_category STRING,
  rating_label STRING,
  label_source STRING,
  text_length BIGINT,
  metadata_matched BOOLEAN
)
PARTITIONED BY (load_batch_id STRING, review_year STRING)
STORED AS PARQUET;

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

WITH prepared AS (
  SELECT
    sha2(concat(coalesce(r.user_id,''), '|#|', coalesce(r.asin,''), '|#|',
                coalesce(r.parent_asin,''), '|#|', coalesce(cast(r.review_timestamp AS STRING),''), '|#|',
                coalesce(r.title,''), '|#|', coalesce(r.review_text,'')), 256) AS review_key,
    r.asin,
    r.parent_asin,
    r.user_id,
    r.rating,
    r.title,
    r.review_text,
    regexp_replace(regexp_replace(trim(r.review_text), '[\\r\\n\\t]+', ' '), '\\s+', ' ') AS review_text_clean,
    r.review_timestamp,
    cast(from_unixtime(cast(r.review_timestamp / 1000 AS BIGINT)) AS TIMESTAMP) AS review_time,
    from_unixtime(cast(r.review_timestamp / 1000 AS BIGINT), 'yyyy-MM-dd') AS dt,
    r.helpful_vote,
    r.verified_purchase,
    m.product_title,
    m.store_name,
    m.main_category,
    CASE WHEN r.rating <= 2 THEN 'negative'
         WHEN r.rating = 3 THEN 'neutral'
         WHEN r.rating >= 4 THEN 'positive'
         ELSE 'unknown' END AS rating_label,
    'rating_weak_label' AS label_source,
    cast(length(regexp_replace(regexp_replace(trim(r.review_text), '[\\r\\n\\t]+', ' '), '\\s+', ' ')) AS BIGINT) AS text_length,
    CASE WHEN m.parent_asin IS NOT NULL THEN true ELSE false END AS metadata_matched,
    from_unixtime(cast(r.review_timestamp / 1000 AS BIGINT), 'yyyy') AS review_year
  FROM review_dw.ods_amazon_fashion_review r
  LEFT JOIN review_dw.ods_amazon_fashion_meta m
    ON r.parent_asin=m.parent_asin AND m.load_batch_id='prod_v1_100k'
  WHERE r.load_batch_id='prod_v1_100k'
    AND r.review_text IS NOT NULL
    AND trim(r.review_text)<>''
), ranked AS (
  SELECT prepared.*,
         row_number() OVER (PARTITION BY review_key ORDER BY review_timestamp, asin, parent_asin) AS duplicate_rank
  FROM prepared
)
INSERT OVERWRITE TABLE review_dw.dwd_amazon_fashion_review
PARTITION (load_batch_id='prod_v1_100k', review_year)
SELECT
  review_key, asin, parent_asin, user_id, rating, title, review_text, review_text_clean,
  review_timestamp, review_time, dt, helpful_vote, verified_purchase, product_title,
  store_name, main_category, rating_label, label_source, text_length, metadata_matched,
  review_year
FROM ranked
WHERE duplicate_rank=1;
