USE review_dw;

-- Every query returns aggregate evidence only. assert_true aborts the runner on
-- any contract or source-reconciliation failure.
SELECT 'category',COUNT(*),SUM(review_count),
 assert_true(SUM(review_count)=99703 AND SUM(CASE WHEN category_key IS NULL OR main_category IS NULL OR review_count<>positive_count+neutral_count+negative_count OR positive_rate NOT BETWEEN 0 AND 1 OR neutral_rate NOT BETWEEN 0 AND 1 OR negative_rate NOT BETWEEN 0 AND 1 THEN 1 ELSE 0 END)=0)
FROM dws_category_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';
SELECT 'DUPLICATE_FOUND' FROM dws_category_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' GROUP BY category_key HAVING COUNT(*)>1 LIMIT 1;

SELECT 'store',COUNT(*),SUM(review_count),
 assert_true(SUM(review_count)=99703 AND SUM(CASE WHEN store_key IS NULL OR store_name IS NULL OR review_count<>positive_count+neutral_count+negative_count OR positive_rate NOT BETWEEN 0 AND 1 OR neutral_rate NOT BETWEEN 0 AND 1 OR negative_rate NOT BETWEEN 0 AND 1 THEN 1 ELSE 0 END)=0)
FROM dws_store_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';
SELECT 'DUPLICATE_FOUND' FROM dws_store_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' GROUP BY store_key HAVING COUNT(*)>1 LIMIT 1;

SELECT 'verified_purchase',COUNT(*),SUM(review_count),
 assert_true(SUM(review_count)=99703 AND SUM(CASE WHEN purchase_status NOT IN ('verified','unverified','unknown') OR review_count<>positive_count+neutral_count+negative_count OR positive_rate NOT BETWEEN 0 AND 1 OR neutral_rate NOT BETWEEN 0 AND 1 OR negative_rate NOT BETWEEN 0 AND 1 THEN 1 ELSE 0 END)=0)
FROM dws_verified_purchase_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';
SELECT 'DUPLICATE_FOUND' FROM dws_verified_purchase_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' GROUP BY purchase_status HAVING COUNT(*)>1 LIMIT 1;

SELECT 'rating_matrix',COUNT(*),SUM(review_count),
 assert_true(SUM(review_count)=99703 AND SUM(CASE WHEN rating_value NOT BETWEEN 1 AND 5 OR pred_label NOT IN ('negative','neutral','positive') OR rate_within_rating NOT BETWEEN 0 AND 1 THEN 1 ELSE 0 END)=0)
FROM dws_rating_prediction_matrix WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';
SELECT 'DUPLICATE_FOUND' FROM dws_rating_prediction_matrix WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' GROUP BY rating_value,pred_label HAVING COUNT(*)>1 LIMIT 1;
SELECT 'rating_rate_sums',rating_value,SUM(rate_within_rating),assert_true(abs(SUM(rate_within_rating)-1.0)<=0.000001) FROM dws_rating_prediction_matrix WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' GROUP BY rating_value;

SELECT 'confidence',COUNT(*),SUM(review_count),
 assert_true(COUNT(*)=4 AND SUM(CASE WHEN bucket_code='low' THEN 1 ELSE 0 END)=1 AND SUM(CASE WHEN bucket_code='medium' THEN 1 ELSE 0 END)=1 AND SUM(CASE WHEN bucket_code='high' THEN 1 ELSE 0 END)=1 AND SUM(CASE WHEN bucket_code='very_high' THEN 1 ELSE 0 END)=1 AND SUM(review_count)=99703 AND SUM(CASE WHEN bucket_code NOT IN ('low','medium','high','very_high') OR average_prediction_score NOT BETWEEN 0 AND 1 OR review_count<>positive_count+neutral_count+negative_count THEN 1 ELSE 0 END)=0)
FROM dws_prediction_confidence WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

SELECT 'monthly',COUNT(*),SUM(review_count),
 assert_true(COUNT(*)=200 AND SUM(review_count)=99703 AND SUM(CASE WHEN month_id NOT RLIKE '^[0-9]{4}-(0[1-9]|1[0-2])$' OR review_count<>positive_count+neutral_count+negative_count OR positive_rate NOT BETWEEN 0 AND 1 OR neutral_rate NOT BETWEEN 0 AND 1 OR negative_rate NOT BETWEEN 0 AND 1 THEN 1 ELSE 0 END)=0)
FROM dws_monthly_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

SELECT 'alerts',COUNT(*),
 assert_true(COUNT(*)=179 AND SUM(CASE WHEN alert_id IS NULL OR alert_type IS NULL OR alert_level NOT IN ('high','medium') OR lower(concat_ws(' ',entity_id,entity_name,alert_message)) RLIKE '(smoke[_ -]?test|synthetic[_ -]?test|test[_ -]?row)' THEN 1 ELSE 0 END)=0)
FROM dws_sentiment_alerts WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

SELECT 'samples',COUNT(*),
 assert_true(COUNT(*)=150 AND SUM(CASE WHEN sample_id IS NULL OR pred_label NOT IN ('negative','neutral','positive') OR length(review_text_preview)>180 OR review_text_preview RLIKE '[\\r\\n\\t]' OR lower(concat_ws(' ',product_title,main_category,review_text_preview)) RLIKE '(smoke[_ -]?test|synthetic[_ -]?test|test[_ -]?row)' THEN 1 ELSE 0 END)=0)
FROM dws_review_samples WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';
SELECT 'sample_label_limits',pred_label,COUNT(*),assert_true(COUNT(*)<=50) FROM dws_review_samples WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' GROUP BY pred_label;

SELECT 'aspects',COUNT(*),SUM(mention_count),
 assert_true(COUNT(*)=8 AND SUM(CASE WHEN aspect_code IS NULL OR extraction_method<>'keyword_rules_v1' OR rule_version<>'fashion_aspects_v1' OR mention_count<>positive_count+neutral_count+negative_count OR positive_rate NOT BETWEEN 0 AND 1 OR neutral_rate NOT BETWEEN 0 AND 1 OR negative_rate NOT BETWEEN 0 AND 1 THEN 1 ELSE 0 END)=0)
FROM dws_aspect_summary WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

SELECT 'negative_reasons',COUNT(*),SUM(mention_count),
 assert_true(COUNT(*)=9 AND SUM(CASE WHEN reason_code IS NULL OR extraction_method<>'keyword_rules_v1' OR rule_version<>'negative_reasons_v1' OR mention_count>15899 OR share_of_negative_reviews NOT BETWEEN 0 AND 1 THEN 1 ELSE 0 END)=0)
FROM dws_negative_reasons WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

SELECT 'source_join',COUNT(*),assert_true(COUNT(*)=99703)
FROM vw_dwd_review_with_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';
