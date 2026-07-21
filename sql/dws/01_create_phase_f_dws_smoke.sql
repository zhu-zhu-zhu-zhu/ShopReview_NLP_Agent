USE review_dw;

DROP TABLE IF EXISTS dws_sentiment_overview_smoke;
CREATE TABLE dws_sentiment_overview_smoke (
  review_count BIGINT,
  user_count BIGINT,
  product_count BIGINT,
  positive_count BIGINT,
  neutral_count BIGINT,
  negative_count BIGINT,
  positive_rate DOUBLE,
  neutral_rate DOUBLE,
  negative_rate DOUBLE,
  average_rating DOUBLE,
  generated_at TIMESTAMP,
  data_scope STRING
)
STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_sentiment_overview_smoke
SELECT
  COUNT(*),
  COUNT(DISTINCT user_id),
  COUNT(DISTINCT parent_asin),
  SUM(CASE WHEN COALESCE(pred_label, rating_label)='positive' THEN 1 ELSE 0 END),
  SUM(CASE WHEN COALESCE(pred_label, rating_label)='neutral' THEN 1 ELSE 0 END),
  SUM(CASE WHEN COALESCE(pred_label, rating_label)='negative' THEN 1 ELSE 0 END),
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN COALESCE(pred_label, rating_label)='positive' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN COALESCE(pred_label, rating_label)='neutral' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN COALESCE(pred_label, rating_label)='negative' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  AVG(rating),
  current_timestamp,
  'phase_d_e_smoke_contract'
FROM vw_dwd_review_with_sentiment_smoke;

DROP TABLE IF EXISTS dws_product_sentiment_smoke;
CREATE TABLE dws_product_sentiment_smoke (
  parent_asin STRING,
  product_title STRING,
  store_name STRING,
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
  generated_at TIMESTAMP,
  data_scope STRING
)
STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_product_sentiment_smoke
SELECT
  parent_asin,
  product_title,
  store_name,
  COUNT(*),
  AVG(rating),
  SUM(CASE WHEN COALESCE(pred_label, rating_label)='positive' THEN 1 ELSE 0 END),
  SUM(CASE WHEN COALESCE(pred_label, rating_label)='neutral' THEN 1 ELSE 0 END),
  SUM(CASE WHEN COALESCE(pred_label, rating_label)='negative' THEN 1 ELSE 0 END),
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN COALESCE(pred_label, rating_label)='positive' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN COALESCE(pred_label, rating_label)='neutral' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN COALESCE(pred_label, rating_label)='negative' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN verified_purchase THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  AVG(CAST(helpful_vote AS DOUBLE)),
  current_timestamp,
  'phase_d_e_smoke_contract'
FROM vw_dwd_review_with_sentiment_smoke
GROUP BY parent_asin, product_title, store_name;

DROP TABLE IF EXISTS dws_aspect_summary_smoke;
CREATE TABLE dws_aspect_summary_smoke (
  aspect STRING,
  reason_code STRING,
  reason_name STRING,
  mention_count BIGINT,
  negative_count BIGINT,
  neutral_count BIGINT,
  positive_count BIGINT,
  negative_rate DOUBLE,
  average_confidence DOUBLE,
  extractor_version STRING,
  generated_at TIMESTAMP,
  data_scope STRING
)
STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_aspect_summary_smoke
SELECT
  aspect,
  reason_code,
  reason_name,
  COUNT(*),
  SUM(CASE WHEN aspect_sentiment='negative' THEN 1 ELSE 0 END),
  SUM(CASE WHEN aspect_sentiment='neutral' THEN 1 ELSE 0 END),
  SUM(CASE WHEN aspect_sentiment='positive' THEN 1 ELSE 0 END),
  CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN aspect_sentiment='negative' THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END,
  AVG(confidence),
  extractor_version,
  current_timestamp,
  'synthetic_aspect_contract_smoke'
FROM dwd_review_aspect_contract_smoke
GROUP BY aspect, reason_code, reason_name, extractor_version;

DROP TABLE IF EXISTS dws_negative_reason_smoke;
CREATE TABLE dws_negative_reason_smoke (
  parent_asin STRING,
  product_title STRING,
  aspect STRING,
  reason_code STRING,
  reason_name STRING,
  reason_count BIGINT,
  reason_share DOUBLE,
  extractor_version STRING,
  generated_at TIMESTAMP,
  data_scope STRING
)
STORED AS PARQUET;

WITH reason_counts AS (
  SELECT
    d.parent_asin,
    d.product_title,
    a.aspect,
    a.reason_code,
    a.reason_name,
    a.extractor_version,
    COUNT(*) AS reason_count
  FROM dwd_review_aspect_contract_smoke a
  JOIN dwd_amazon_fashion_review_smoke d ON a.review_key=d.review_key
  WHERE a.aspect_sentiment='negative'
  GROUP BY d.parent_asin, d.product_title, a.aspect, a.reason_code, a.reason_name, a.extractor_version
), product_totals AS (
  SELECT d.parent_asin, COUNT(*) AS negative_aspect_count
  FROM dwd_review_aspect_contract_smoke a
  JOIN dwd_amazon_fashion_review_smoke d ON a.review_key=d.review_key
  WHERE a.aspect_sentiment='negative'
  GROUP BY d.parent_asin
)
INSERT OVERWRITE TABLE dws_negative_reason_smoke
SELECT
  r.parent_asin,
  r.product_title,
  r.aspect,
  r.reason_code,
  r.reason_name,
  r.reason_count,
  CASE WHEN p.negative_aspect_count=0 THEN 0.0 ELSE CAST(r.reason_count AS DOUBLE)/p.negative_aspect_count END,
  r.extractor_version,
  current_timestamp,
  'synthetic_aspect_contract_smoke'
FROM reason_counts r
JOIN product_totals p ON r.parent_asin=p.parent_asin;
