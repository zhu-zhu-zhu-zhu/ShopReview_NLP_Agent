CREATE DATABASE IF NOT EXISTS review_dw;

DROP TABLE IF EXISTS review_dw.dwd_amazon_fashion_review_smoke;
CREATE TABLE IF NOT EXISTS review_dw.dwd_amazon_fashion_review_smoke (
  review_key STRING, asin STRING, parent_asin STRING, user_id STRING,
  rating DOUBLE, title STRING, review_text STRING, review_text_clean STRING,
  review_timestamp BIGINT, review_time TIMESTAMP, dt STRING, helpful_vote BIGINT,
  verified_purchase BOOLEAN, product_title STRING, store_name STRING,
  main_category STRING, rating_label STRING, label_source STRING, text_length BIGINT
)
STORED AS PARQUET;

INSERT OVERWRITE TABLE review_dw.dwd_amazon_fashion_review_smoke
SELECT
  sha2(concat(coalesce(r.user_id,''), '|#|', coalesce(r.asin,''), '|#|',
              coalesce(r.parent_asin,''), '|#|', coalesce(cast(r.review_timestamp AS STRING),''), '|#|',
              coalesce(r.title,''), '|#|', coalesce(r.review_text,'')), 256) AS review_key,
  r.asin, r.parent_asin, r.user_id, r.rating, r.title, r.review_text,
  regexp_replace(regexp_replace(trim(r.review_text), '[\\r\\n\\t]+', ' '), '\\s+', ' ') AS review_text_clean,
  r.review_timestamp,
  cast(from_unixtime(cast(r.review_timestamp / 1000 AS BIGINT)) AS TIMESTAMP) AS review_time,
  from_unixtime(cast(r.review_timestamp / 1000 AS BIGINT), 'yyyy-MM-dd') AS dt,
  r.helpful_vote, r.verified_purchase, m.product_title, m.store_name, m.main_category,
  CASE WHEN r.rating <= 2 THEN 'negative'
       WHEN r.rating = 3 THEN 'neutral'
       WHEN r.rating >= 4 THEN 'positive'
       ELSE 'unknown' END AS rating_label,
  'rating_weak_label' AS label_source,
  cast(length(regexp_replace(regexp_replace(trim(r.review_text), '[\\r\\n\\t]+', ' '), '\\s+', ' ')) AS BIGINT) AS text_length
FROM review_dw.ods_amazon_fashion_review_matched_smoke r
JOIN review_dw.ods_amazon_fashion_meta_matched_smoke m
  ON r.parent_asin = m.parent_asin
WHERE r.review_text IS NOT NULL AND trim(r.review_text) <> '';
