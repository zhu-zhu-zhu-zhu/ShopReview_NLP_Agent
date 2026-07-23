-- Set these values in your SQL client before running:
SET @batch_id = 'prod_v1_100k';
SET @model_version = 'tfidf_logreg_oof_v1';

SELECT COUNT(*) AS overview_rows FROM shopreview_serving.dws_sentiment_overview
WHERE load_batch_id=@batch_id AND model_version=@model_version;
SELECT COUNT(*) AS daily_rows FROM shopreview_serving.dws_sentiment_daily
WHERE load_batch_id=@batch_id AND model_version=@model_version;
SELECT COUNT(*) AS product_rows FROM shopreview_serving.dws_product_sentiment
WHERE load_batch_id=@batch_id AND model_version=@model_version;

SELECT review_count AS overview_review_count
FROM shopreview_serving.dws_sentiment_overview
WHERE load_batch_id=@batch_id AND model_version=@model_version;

SELECT review_count, positive_count + neutral_count + negative_count AS sentiment_count_sum
FROM shopreview_serving.dws_sentiment_overview
WHERE load_batch_id=@batch_id AND model_version=@model_version;

SELECT COUNT(*) AS invalid_rate_rows FROM (
  SELECT positive_rate, neutral_rate, negative_rate FROM shopreview_serving.dws_sentiment_overview
  WHERE load_batch_id=@batch_id AND model_version=@model_version
  UNION ALL
  SELECT positive_rate, neutral_rate, negative_rate FROM shopreview_serving.dws_sentiment_daily
  WHERE load_batch_id=@batch_id AND model_version=@model_version
  UNION ALL
  SELECT positive_rate, neutral_rate, negative_rate FROM shopreview_serving.dws_product_sentiment
  WHERE load_batch_id=@batch_id AND model_version=@model_version
) AS rates
WHERE positive_rate NOT BETWEEN 0 AND 1
   OR neutral_rate NOT BETWEEN 0 AND 1
   OR negative_rate NOT BETWEEN 0 AND 1;

SELECT SUM(review_count) AS daily_review_count_sum
FROM shopreview_serving.dws_sentiment_daily
WHERE load_batch_id=@batch_id AND model_version=@model_version;
SELECT SUM(review_count) AS product_review_count_sum
FROM shopreview_serving.dws_product_sentiment
WHERE load_batch_id=@batch_id AND model_version=@model_version;

SELECT COUNT(*) AS duplicate_overview_keys FROM (
  SELECT load_batch_id, model_version FROM shopreview_serving.dws_sentiment_overview
  GROUP BY load_batch_id, model_version HAVING COUNT(*)>1
) AS duplicates;
SELECT COUNT(*) AS duplicate_daily_keys FROM (
  SELECT dt, load_batch_id, model_version FROM shopreview_serving.dws_sentiment_daily
  GROUP BY dt, load_batch_id, model_version HAVING COUNT(*)>1
) AS duplicates;
SELECT COUNT(*) AS duplicate_product_keys FROM (
  SELECT parent_asin, load_batch_id, model_version FROM shopreview_serving.dws_product_sentiment
  GROUP BY parent_asin, load_batch_id, model_version HAVING COUNT(*)>1
) AS duplicates;

SELECT COUNT(*) AS unexpected_batch_rows FROM (
  SELECT load_batch_id FROM shopreview_serving.dws_sentiment_overview
  UNION ALL SELECT load_batch_id FROM shopreview_serving.dws_sentiment_daily
  UNION ALL SELECT load_batch_id FROM shopreview_serving.dws_product_sentiment
) AS all_rows WHERE load_batch_id<>@batch_id;
SELECT COUNT(*) AS unexpected_model_rows FROM (
  SELECT model_version FROM shopreview_serving.dws_sentiment_overview
  UNION ALL SELECT model_version FROM shopreview_serving.dws_sentiment_daily
  UNION ALL SELECT model_version FROM shopreview_serving.dws_product_sentiment
) AS all_rows WHERE model_version<>@model_version;

SELECT parent_asin, product_title, review_count, positive_rate, negative_rate
FROM shopreview_serving.dws_product_sentiment
WHERE load_batch_id=@batch_id AND model_version=@model_version
ORDER BY review_count DESC, parent_asin LIMIT 10;

SELECT parent_asin, product_title, review_count, negative_rate
FROM shopreview_serving.dws_product_sentiment
WHERE load_batch_id=@batch_id AND model_version=@model_version AND review_count>=5
ORDER BY negative_rate DESC, review_count DESC, parent_asin LIMIT 10;

SELECT dt, review_count, positive_rate, neutral_rate, negative_rate
FROM shopreview_serving.dws_sentiment_daily
WHERE load_batch_id=@batch_id AND model_version=@model_version
ORDER BY dt DESC LIMIT 10;
