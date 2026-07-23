USE review_dw;

SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;
SET hive.merge.mapfiles=false;
SET hive.merge.mapredfiles=false;
SET hive.merge.tezfiles=false;

CREATE TABLE IF NOT EXISTS dws_category_sentiment (
  category_key STRING, main_category STRING, review_count BIGINT, product_count BIGINT,
  average_rating DOUBLE, positive_count BIGINT, neutral_count BIGINT, negative_count BIGINT,
  positive_rate DOUBLE, neutral_rate DOUBLE, negative_rate DOUBLE,
  average_prediction_score DOUBLE, generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_category_sentiment
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT sha2(lower(trim(category_name)),256), category_name, COUNT(*), COUNT(DISTINCT parent_asin),
       AVG(rating),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       AVG(pred_score), current_timestamp
FROM (
  SELECT CASE WHEN main_category IS NULL OR trim(main_category)='' THEN 'Unknown' ELSE trim(main_category) END category_name,
         parent_asin, rating, pred_label, pred_score
  FROM vw_dwd_review_with_sentiment
  WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}'
) s GROUP BY category_name;

CREATE TABLE IF NOT EXISTS dws_store_sentiment (
  store_key STRING, store_name STRING, review_count BIGINT, product_count BIGINT,
  average_rating DOUBLE, positive_count BIGINT, neutral_count BIGINT, negative_count BIGINT,
  positive_rate DOUBLE, neutral_rate DOUBLE, negative_rate DOUBLE,
  average_prediction_score DOUBLE, generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_store_sentiment
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT sha2(lower(trim(normalized_store)),256), normalized_store, COUNT(*), COUNT(DISTINCT parent_asin),
       AVG(rating),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       AVG(pred_score), current_timestamp
FROM (
  SELECT CASE WHEN store_name IS NULL OR trim(store_name)='' THEN 'Unknown' ELSE lower(trim(store_name)) END normalized_store,
         parent_asin, rating, pred_label, pred_score
  FROM vw_dwd_review_with_sentiment
  WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}'
) s GROUP BY normalized_store;

CREATE TABLE IF NOT EXISTS dws_verified_purchase_sentiment (
  purchase_status STRING, review_count BIGINT, positive_count BIGINT, neutral_count BIGINT,
  negative_count BIGINT, positive_rate DOUBLE, neutral_rate DOUBLE, negative_rate DOUBLE,
  average_rating DOUBLE, average_helpful_vote DOUBLE, average_prediction_score DOUBLE,
  generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_verified_purchase_sentiment
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT purchase_status, COUNT(*),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       AVG(rating), AVG(CAST(helpful_vote AS DOUBLE)), AVG(pred_score), current_timestamp
FROM (
  SELECT CASE WHEN verified_purchase=true THEN 'verified'
              WHEN verified_purchase=false THEN 'unverified' ELSE 'unknown' END purchase_status,
         rating, helpful_vote, pred_label, pred_score
  FROM vw_dwd_review_with_sentiment
  WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}'
) s GROUP BY purchase_status;

CREATE TABLE IF NOT EXISTS dws_rating_prediction_matrix (
  rating_value INT, pred_label STRING, review_count BIGINT, rate_within_rating DOUBLE,
  generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_rating_prediction_matrix
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT rating_value, pred_label, COUNT(*), COUNT(*)/CAST(MAX(rating_total) AS DOUBLE), current_timestamp
FROM (
  SELECT CAST(rating AS INT) rating_value, pred_label,
         COUNT(*) OVER (PARTITION BY CAST(rating AS INT)) rating_total
  FROM vw_dwd_review_with_sentiment
  WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}'
    AND CAST(rating AS INT) BETWEEN 1 AND 5
) s GROUP BY rating_value, pred_label;

CREATE TABLE IF NOT EXISTS dws_prediction_confidence (
  bucket_code STRING, bucket_order INT, minimum_score DOUBLE, maximum_score DOUBLE,
  review_count BIGINT, positive_count BIGINT, neutral_count BIGINT, negative_count BIGINT,
  average_prediction_score DOUBLE, generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_prediction_confidence
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT bucket_code, bucket_order, minimum_score, maximum_score, COUNT(*),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
       AVG(pred_score), current_timestamp
FROM (
  SELECT pred_label, pred_score,
    CASE WHEN pred_score<0.50 THEN 'low' WHEN pred_score<0.75 THEN 'medium'
         WHEN pred_score<0.90 THEN 'high' ELSE 'very_high' END bucket_code,
    CASE WHEN pred_score<0.50 THEN 1 WHEN pred_score<0.75 THEN 2
         WHEN pred_score<0.90 THEN 3 ELSE 4 END bucket_order,
    CASE WHEN pred_score<0.50 THEN 0.00 WHEN pred_score<0.75 THEN 0.50
         WHEN pred_score<0.90 THEN 0.75 ELSE 0.90 END minimum_score,
    CASE WHEN pred_score<0.50 THEN 0.50 WHEN pred_score<0.75 THEN 0.75
         WHEN pred_score<0.90 THEN 0.90 ELSE 1.00 END maximum_score
  FROM vw_dwd_review_with_sentiment
  WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}'
    AND pred_score BETWEEN 0.0 AND 1.0
) s GROUP BY bucket_code,bucket_order,minimum_score,maximum_score;

CREATE TABLE IF NOT EXISTS dws_monthly_sentiment (
  month_id STRING, review_count BIGINT, product_count BIGINT, positive_count BIGINT,
  neutral_count BIGINT, negative_count BIGINT, positive_rate DOUBLE, neutral_rate DOUBLE,
  negative_rate DOUBLE, average_rating DOUBLE, average_prediction_score DOUBLE,
  generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_monthly_sentiment
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT substr(dt,1,7), COUNT(*), COUNT(DISTINCT parent_asin),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END),
       SUM(CASE WHEN pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       SUM(CASE WHEN pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
       AVG(rating), AVG(pred_score), current_timestamp
FROM vw_dwd_review_with_sentiment
WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}'
GROUP BY substr(dt,1,7);

CREATE TABLE IF NOT EXISTS dws_sentiment_alerts (
  alert_id STRING, alert_type STRING, alert_level STRING, entity_type STRING,
  entity_id STRING, entity_name STRING, metric_name STRING, metric_value DOUBLE,
  threshold_value DOUBLE, review_count BIGINT, alert_message STRING, generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_sentiment_alerts
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT sha2(concat(alert_type,'|#|',entity_id,'|#|','${hiveconf:dashboard_batch_id}','|#|','${hiveconf:dashboard_model_version}'),256),
       alert_type, alert_level, entity_type, entity_id, entity_name, metric_name,
       metric_value, threshold_value, review_count, alert_message, current_timestamp
FROM (
  SELECT 'PRODUCT_HIGH_NEGATIVE_RATE' alert_type,'high' alert_level,'product' entity_type,
         parent_asin entity_id,coalesce(product_title,parent_asin) entity_name,
         'negative_rate' metric_name,negative_rate metric_value,0.50 threshold_value,review_count,
         concat('Product negative rate is ',cast(negative_rate AS STRING)) alert_message
  FROM dws_product_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND review_count>=5 AND negative_rate>=0.50
  UNION ALL
  SELECT 'PRODUCT_LOW_RATING','medium','product',parent_asin,coalesce(product_title,parent_asin),
         'average_rating',average_rating,2.50,review_count,concat('Product average rating is ',cast(average_rating AS STRING))
  FROM dws_product_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND review_count>=5 AND average_rating<=2.50
  UNION ALL
  SELECT 'PRODUCT_LOW_CONFIDENCE','medium','product',parent_asin,coalesce(product_title,parent_asin),
         'average_prediction_score',average_prediction_score,0.55,review_count,concat('Product average prediction score is ',cast(average_prediction_score AS STRING))
  FROM dws_product_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND review_count>=5 AND average_prediction_score<0.55
  UNION ALL
  SELECT 'CATEGORY_NEGATIVE_RISK','high','category',category_key,main_category,'negative_rate',c.negative_rate,
         o.negative_rate+0.10,c.review_count,concat('Category negative rate is ',cast(c.negative_rate AS STRING))
  FROM dws_category_sentiment c JOIN dws_sentiment_overview o
    ON c.load_batch_id=o.load_batch_id AND c.model_version=o.model_version
  WHERE c.load_batch_id='${hiveconf:dashboard_batch_id}' AND c.model_version='${hiveconf:dashboard_model_version}'
    AND c.review_count>=100 AND c.negative_rate>=o.negative_rate+0.10
  UNION ALL
  SELECT 'DAILY_NEGATIVE_SPIKE','high','daily',CAST(d.dt AS STRING),CAST(d.dt AS STRING),'negative_rate',d.negative_rate,
         o.negative_rate+0.15,d.review_count,concat('Daily negative rate is ',cast(d.negative_rate AS STRING))
  FROM dws_sentiment_daily d JOIN dws_sentiment_overview o
    ON d.load_batch_id=o.load_batch_id AND d.model_version=o.model_version
  WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND d.model_version='${hiveconf:dashboard_model_version}'
    AND d.review_count>=10 AND d.negative_rate>=o.negative_rate+0.15
) alerts;

CREATE TABLE IF NOT EXISTS dws_review_samples (
  sample_id STRING, parent_asin STRING, product_title STRING, main_category STRING,
  rating DOUBLE, pred_label STRING, pred_score DOUBLE, review_text_preview STRING,
  text_length BIGINT, review_time TIMESTAMP, sample_rank INT, generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_review_samples
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT sha2(review_key,256), parent_asin, product_title, main_category, rating, pred_label,
       pred_score, substr(regexp_replace(review_text_clean,'[\\r\\n\\t\\x00-\\x1F]+',' '),1,180),
       text_length, review_time, CAST(sample_rank AS INT), current_timestamp
FROM (
  SELECT d.review_key,d.parent_asin,d.product_title,d.main_category,d.rating,p.pred_label,p.pred_score,
         d.review_text_clean,d.text_length,d.review_time,
         row_number() OVER(PARTITION BY p.pred_label ORDER BY p.pred_score DESC,d.review_key) sample_rank
  FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p
    ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id
  WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}'
) ranked WHERE sample_rank<=50;

CREATE TABLE IF NOT EXISTS dws_aspect_summary (
  aspect_code STRING, aspect_name STRING, mention_count BIGINT, product_count BIGINT,
  positive_count BIGINT, neutral_count BIGINT, negative_count BIGINT,
  positive_rate DOUBLE, neutral_rate DOUBLE, negative_rate DOUBLE,
  average_prediction_score DOUBLE, extraction_method STRING, rule_version STRING,
  generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_aspect_summary
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'quality','Quality',COUNT(*),COUNT(DISTINCT d.parent_asin),
 SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),
 SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),
 AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id
WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(quality|well made|poorly made|cheaply made|craftsmanship|defect|defective|flimsy)';

INSERT INTO TABLE dws_aspect_summary PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'size_fit','Size & Fit',COUNT(*),COUNT(DISTINCT d.parent_asin),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(size|sizing|fit|fits|fitting|too small|too big|too large|tight|loose)';

INSERT INTO TABLE dws_aspect_summary PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'material','Material',COUNT(*),COUNT(DISTINCT d.parent_asin),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(material|fabric|cotton|polyester|leather|wool|texture)';

INSERT INTO TABLE dws_aspect_summary PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'comfort','Comfort',COUNT(*),COUNT(DISTINCT d.parent_asin),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(comfort|comfortable|uncomfortable|soft|itchy|scratchy|hurts)';

INSERT INTO TABLE dws_aspect_summary PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'appearance','Appearance',COUNT(*),COUNT(DISTINCT d.parent_asin),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(color|colour|style|design|look|appearance|cute|beautiful|ugly)';

INSERT INTO TABLE dws_aspect_summary PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'price_value','Price & Value',COUNT(*),COUNT(DISTINCT d.parent_asin),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(price|value|worth|expensive|cheap|overpriced|cost)';

INSERT INTO TABLE dws_aspect_summary PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'shipping_packaging','Shipping & Packaging',COUNT(*),COUNT(DISTINCT d.parent_asin),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(shipping|delivery|arrived|package|packaging|late delivery|damaged box)';

INSERT INTO TABLE dws_aspect_summary PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'durability','Durability',COUNT(*),COUNT(DISTINCT d.parent_asin),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END),SUM(CASE WHEN p.pred_label='positive' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='neutral' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),SUM(CASE WHEN p.pred_label='negative' THEN 1 ELSE 0 END)/CAST(COUNT(*) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','fashion_aspects_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND lower(coalesce(d.review_text_clean,'')) rlike '(durable|durability|lasted|lasting|broke|broken|tear|torn|wear out)';

CREATE TABLE IF NOT EXISTS dws_negative_reasons (
  reason_code STRING, reason_name STRING, mention_count BIGINT, product_count BIGINT,
  share_of_negative_reviews DOUBLE, average_prediction_score DOUBLE,
  extraction_method STRING, rule_version STRING, generated_at TIMESTAMP
) PARTITIONED BY (load_batch_id STRING, model_version STRING) STORED AS PARQUET;

INSERT OVERWRITE TABLE dws_negative_reasons
PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'poor_quality','Poor Quality',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp
FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id
JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1
WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(poor quality|bad quality|cheaply made|poorly made|defective|flimsy)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'wrong_size','Wrong Size',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(too small|too large|too big|wrong size|doesn.t fit|did not fit|tight|loose)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'color_mismatch','Color Mismatch',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(wrong color|different color|color mismatch|faded|not the color)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'damaged_item','Damaged Item',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(damaged|broken|torn|stained|cracked|defective)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'not_as_described','Not As Described',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(not as described|different from picture|not like picture|misleading description)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'uncomfortable','Uncomfortable',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(uncomfortable|itchy|scratchy|hurts|painful)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'overpriced','Overpriced',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(overpriced|not worth|too expensive|waste of money)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'delivery_issue','Delivery Issue',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(late delivery|arrived late|shipping issue|damaged package|missing package)';

INSERT INTO TABLE dws_negative_reasons PARTITION (load_batch_id='${hiveconf:dashboard_batch_id}', model_version='${hiveconf:dashboard_model_version}')
SELECT 'return_issue','Return Issue',COUNT(*),COUNT(DISTINCT d.parent_asin),COUNT(*)/CAST(MAX(n.total_negative) AS DOUBLE),AVG(p.pred_score),'keyword_rules_v1','negative_reasons_v1',current_timestamp FROM dwd_amazon_fashion_review d JOIN dwd_review_sentiment p ON d.review_key=p.review_key AND d.load_batch_id=p.load_batch_id JOIN (SELECT COUNT(*) total_negative FROM dwd_review_sentiment WHERE load_batch_id='${hiveconf:dashboard_batch_id}' AND model_version='${hiveconf:dashboard_model_version}' AND pred_label='negative') n ON 1=1 WHERE d.load_batch_id='${hiveconf:dashboard_batch_id}' AND p.model_version='${hiveconf:dashboard_model_version}' AND p.pred_label='negative' AND lower(coalesce(d.review_text_clean,'')) rlike '(return|refund|replacement|exchange)';
