USE review_dw;

SELECT COUNT(*) AS ods_review_count FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';
SELECT COUNT(*) AS ods_metadata_count FROM ods_amazon_fashion_meta WHERE load_batch_id='prod_v1_100k';
SELECT COUNT(DISTINCT parent_asin) AS distinct_review_parent_asin FROM ods_amazon_fashion_review WHERE load_batch_id='prod_v1_100k' AND parent_asin IS NOT NULL AND trim(parent_asin)<>'';
SELECT COUNT(DISTINCT parent_asin) AS distinct_metadata_parent_asin FROM ods_amazon_fashion_meta WHERE load_batch_id='prod_v1_100k' AND parent_asin IS NOT NULL AND trim(parent_asin)<>'';

SELECT COUNT(*) AS reviews_with_metadata
FROM ods_amazon_fashion_review r JOIN ods_amazon_fashion_meta m ON r.parent_asin=m.parent_asin
WHERE r.load_batch_id='prod_v1_100k' AND m.load_batch_id='prod_v1_100k';
SELECT COUNT(*) AS reviews_without_metadata
FROM ods_amazon_fashion_review r LEFT JOIN ods_amazon_fashion_meta m
  ON r.parent_asin=m.parent_asin AND m.load_batch_id='prod_v1_100k'
WHERE r.load_batch_id='prod_v1_100k' AND m.parent_asin IS NULL;
SELECT CASE WHEN COUNT(*)=0 THEN 0.0 ELSE CAST(SUM(CASE WHEN m.parent_asin IS NOT NULL THEN 1 ELSE 0 END) AS DOUBLE)/COUNT(*) END AS metadata_match_rate
FROM ods_amazon_fashion_review r LEFT JOIN ods_amazon_fashion_meta m
  ON r.parent_asin=m.parent_asin AND m.load_batch_id='prod_v1_100k'
WHERE r.load_batch_id='prod_v1_100k';

SELECT COUNT(*) AS empty_ods_review_text FROM ods_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' AND (review_text IS NULL OR trim(review_text)='');
SELECT COUNT(*) AS dwd_count FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';
SELECT COUNT(*) AS raw_eligible_review_count FROM ods_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>'';
SELECT COUNT(DISTINCT sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|',
       coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|',
       coalesce(title,''), '|#|', coalesce(review_text,'')),256)) AS expected_deduplicated_dwd_count
FROM ods_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>'';
SELECT COUNT(*) AS source_duplicate_review_key_groups FROM (
  SELECT sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|',
         coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|',
         coalesce(title,''), '|#|', coalesce(review_text,'')),256) AS source_review_key
  FROM ods_amazon_fashion_review
  WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>''
  GROUP BY sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|',
           coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|',
           coalesce(title,''), '|#|', coalesce(review_text,'')),256)
  HAVING COUNT(*)>1
) source_duplicates;
SELECT SUM(row_count-1) AS source_duplicate_excess_rows FROM (
  SELECT COUNT(*) AS row_count FROM ods_amazon_fashion_review
  WHERE load_batch_id='prod_v1_100k' AND review_text IS NOT NULL AND trim(review_text)<>''
  GROUP BY sha2(concat(coalesce(user_id,''), '|#|', coalesce(asin,''), '|#|',
           coalesce(parent_asin,''), '|#|', coalesce(cast(review_timestamp AS STRING),''), '|#|',
           coalesce(title,''), '|#|', coalesce(review_text,'')),256)
  HAVING COUNT(*)>1
) source_duplicates;
SELECT COUNT(*) AS null_review_key FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' AND (review_key IS NULL OR trim(review_key)='');
SELECT COUNT(*) AS duplicate_review_key_groups FROM (
  SELECT review_key FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k'
  GROUP BY review_key HAVING COUNT(*)>1
) duplicate_keys;
SELECT COUNT(*) AS blank_review_text_clean FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' AND (review_text_clean IS NULL OR trim(review_text_clean)='');
SELECT COUNT(*) AS invalid_rating_label FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' AND rating_label NOT IN ('negative','neutral','positive');
SELECT rating_label, COUNT(*) AS row_count FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' GROUP BY rating_label ORDER BY rating_label;

SELECT COUNT(review_time) AS valid_timestamp_conversion FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';
SELECT COUNT(*) AS invalid_timestamp_conversion FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' AND (review_time IS NULL OR dt IS NULL OR review_year IS NULL);
SELECT metadata_matched, COUNT(*) AS row_count FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' GROUP BY metadata_matched ORDER BY metadata_matched;
SELECT COUNT(product_title) AS product_title_non_null, COUNT(store_name) AS store_name_non_null,
       COUNT(main_category) AS main_category_non_null
FROM dwd_amazon_fashion_review WHERE load_batch_id='prod_v1_100k';

SHOW PARTITIONS dwd_amazon_fashion_review;
SELECT review_year, COUNT(*) AS row_count FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' GROUP BY review_year ORDER BY review_year;
SELECT rating, COUNT(*) AS row_count FROM ods_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' GROUP BY rating ORDER BY rating;
SELECT rating, COUNT(*) AS row_count FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k' GROUP BY rating ORDER BY rating;

SELECT COUNT(*) AS invalid_ods_count_or_value_rows FROM ods_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
  AND (rating IS NULL OR rating<1 OR rating>5 OR helpful_vote IS NULL OR helpful_vote<0 OR verified_purchase IS NULL);
SELECT COUNT(*) AS invalid_dwd_count_or_rate_rows FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
  AND (text_length IS NULL OR text_length<=0 OR metadata_matched IS NULL);

SELECT substr(review_key,1,12) AS review_key_prefix, asin, parent_asin, rating, rating_label,
       dt, metadata_matched, product_title, store_name, substr(review_text_clean,1,80) AS review_text_preview
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
ORDER BY review_key_prefix LIMIT 10;
