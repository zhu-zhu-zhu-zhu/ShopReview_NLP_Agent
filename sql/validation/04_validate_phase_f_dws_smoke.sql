USE review_dw;

SELECT COUNT(*) AS sentiment_overview_rows FROM dws_sentiment_overview_smoke;
SELECT review_count AS overview_review_count FROM dws_sentiment_overview_smoke;
SELECT COUNT(*) AS prediction_view_count FROM vw_dwd_review_with_sentiment_smoke;
SELECT review_count, positive_count + neutral_count + negative_count AS sentiment_count_sum
FROM dws_sentiment_overview_smoke;
SELECT COUNT(*) AS invalid_overview_rate_rows FROM dws_sentiment_overview_smoke
WHERE positive_rate<0 OR positive_rate>1 OR neutral_rate<0 OR neutral_rate>1 OR negative_rate<0 OR negative_rate>1;
SELECT SUM(review_count) AS product_review_count_sum FROM dws_product_sentiment_smoke;
SELECT COUNT(*) AS invalid_product_rate_rows FROM dws_product_sentiment_smoke
WHERE positive_rate<0 OR positive_rate>1 OR neutral_rate<0 OR neutral_rate>1 OR negative_rate<0 OR negative_rate>1
   OR verified_purchase_rate<0 OR verified_purchase_rate>1;
SELECT COUNT(*) AS matched_aspect_rows
FROM dwd_review_aspect_contract_smoke a JOIN dwd_amazon_fashion_review_smoke d ON a.review_key=d.review_key;
SELECT COUNT(*) AS unknown_aspect_review_keys
FROM dwd_review_aspect_contract_smoke a LEFT JOIN dwd_amazon_fashion_review_smoke d ON a.review_key=d.review_key
WHERE d.review_key IS NULL;
SELECT COUNT(*) AS duplicate_aspect_contract_keys FROM (
  SELECT review_key, aspect, reason_code, extractor_version
  FROM dwd_review_aspect_contract_smoke
  GROUP BY review_key, aspect, reason_code, extractor_version HAVING COUNT(*)>1
) duplicates;
SELECT COUNT(*) AS invalid_aspects FROM dwd_review_aspect_contract_smoke
WHERE aspect NOT IN ('size','color','material','comfort','workmanship','description_mismatch','packaging','delivery','price','other');
SELECT COUNT(*) AS invalid_aspect_labels FROM dwd_review_aspect_contract_smoke
WHERE aspect_sentiment NOT IN ('negative','neutral','positive');
SELECT COUNT(*) AS invalid_confidence_values FROM dwd_review_aspect_contract_smoke
WHERE confidence IS NULL OR confidence<0 OR confidence>1;
SELECT COUNT(*) AS aspect_contract_rows FROM dwd_review_aspect_contract_smoke;
SELECT SUM(mention_count) AS aspect_mention_sum FROM dws_aspect_summary_smoke;
SELECT COUNT(*) AS negative_aspect_rows FROM dwd_review_aspect_contract_smoke WHERE aspect_sentiment='negative';
SELECT SUM(reason_count) AS negative_reason_sum FROM dws_negative_reason_smoke;
SELECT COUNT(*) AS invalid_reason_share_rows FROM dws_negative_reason_smoke
WHERE reason_share<0 OR reason_share>1;

SELECT * FROM dws_sentiment_overview_smoke LIMIT 1;
SELECT parent_asin, product_title, review_count, positive_rate, neutral_rate, negative_rate
FROM dws_product_sentiment_smoke ORDER BY parent_asin LIMIT 5;
SELECT aspect, reason_code, mention_count, negative_count, negative_rate, extractor_version
FROM dws_aspect_summary_smoke ORDER BY aspect, reason_code LIMIT 10;
SELECT parent_asin, aspect, reason_code, reason_count, reason_share, extractor_version
FROM dws_negative_reason_smoke ORDER BY parent_asin, aspect, reason_code LIMIT 10;
