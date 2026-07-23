USE review_dw;

-- Runtime data is written inside the HiveServer2 container and copied to an
-- ignored local directory by scripts/run_dashboard_dws_v2.ps1.

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/category'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT category_key,main_category,review_count,product_count,average_rating,
       positive_count,neutral_count,negative_count,positive_rate,neutral_rate,
       negative_rate,average_prediction_score,generated_at,load_batch_id,model_version
FROM dws_category_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/store'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT store_key,store_name,review_count,product_count,average_rating,
       positive_count,neutral_count,negative_count,positive_rate,neutral_rate,
       negative_rate,average_prediction_score,generated_at,load_batch_id,model_version
FROM dws_store_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/verified_purchase'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT purchase_status,review_count,positive_count,neutral_count,negative_count,
       positive_rate,neutral_rate,negative_rate,average_rating,average_helpful_vote,
       average_prediction_score,generated_at,load_batch_id,model_version
FROM dws_verified_purchase_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/rating_matrix'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT rating_value,pred_label,review_count,rate_within_rating,generated_at,load_batch_id,model_version
FROM dws_rating_prediction_matrix WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/confidence'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT bucket_code,bucket_order,minimum_score,maximum_score,review_count,
       positive_count,neutral_count,negative_count,average_prediction_score,
       generated_at,load_batch_id,model_version
FROM dws_prediction_confidence WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/monthly'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT month_id,review_count,product_count,positive_count,neutral_count,negative_count,
       positive_rate,neutral_rate,negative_rate,average_rating,average_prediction_score,
       generated_at,load_batch_id,model_version
FROM dws_monthly_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/alerts'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT alert_id,alert_type,alert_level,entity_type,entity_id,entity_name,metric_name,
       metric_value,threshold_value,review_count,alert_message,generated_at,load_batch_id,model_version
FROM dws_sentiment_alerts WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/samples'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT sample_id,parent_asin,product_title,main_category,rating,pred_label,pred_score,
       review_text_preview,text_length,review_time,sample_rank,generated_at,load_batch_id,model_version
FROM dws_review_samples WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/aspects'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT aspect_code,aspect_name,mention_count,product_count,positive_count,neutral_count,
       negative_count,positive_rate,neutral_rate,negative_rate,average_prediction_score,
       extraction_method,rule_version,generated_at,load_batch_id,model_version
FROM dws_aspect_summary WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';

INSERT OVERWRITE LOCAL DIRECTORY '/tmp/shopreview_dashboard_v2_export/reasons'
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\001' NULL DEFINED AS '\\N'
SELECT reason_code,reason_name,mention_count,product_count,share_of_negative_reviews,
       average_prediction_score,extraction_method,rule_version,generated_at,load_batch_id,model_version
FROM dws_negative_reasons WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}';
