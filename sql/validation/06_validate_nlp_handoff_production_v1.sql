USE review_dw;

SELECT COUNT(*) AS production_dwd_row_count
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k';

SELECT COUNT(*) AS eligible_nlp_input_row_count
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
  AND review_text_clean IS NOT NULL AND TRIM(review_text_clean)<>''
  AND review_key IS NOT NULL AND TRIM(review_key)<>''
  AND rating_label IN ('negative','neutral','positive');

SELECT COUNT(*) AS null_or_blank_review_key_count
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
  AND (review_key IS NULL OR TRIM(review_key)='');

SELECT COUNT(*) AS duplicate_review_key_group_count
FROM (
  SELECT review_key
  FROM dwd_amazon_fashion_review
  WHERE load_batch_id='prod_v1_100k'
  GROUP BY review_key
  HAVING COUNT(*)>1
) duplicate_keys;

SELECT COUNT(*) AS blank_review_text_clean_count
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
  AND (review_text_clean IS NULL OR TRIM(review_text_clean)='');

SELECT COUNT(*) AS invalid_rating_label_count
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
  AND (rating_label IS NULL OR rating_label NOT IN ('negative','neutral','positive'));

SELECT rating_label, COUNT(*) AS row_count
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
GROUP BY rating_label
ORDER BY rating_label;

SELECT rating, COUNT(*) AS row_count
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k'
GROUP BY rating
ORDER BY rating;

SELECT
  COUNT(parent_asin) AS rows_with_parent_asin,
  COUNT(main_category) AS rows_with_main_category,
  COUNT(review_time) AS rows_with_review_time
FROM dwd_amazon_fashion_review
WHERE load_batch_id='prod_v1_100k';

SELECT COUNT(*) AS export_table_row_count
FROM tmp_nlp_input_prod_v1_100k;

SELECT
  export_counts.export_count - eligible_counts.eligible_count
  AS export_eligible_row_difference
FROM (
  SELECT load_batch_id, COUNT(*) AS export_count
  FROM tmp_nlp_input_prod_v1_100k
  WHERE load_batch_id='prod_v1_100k'
  GROUP BY load_batch_id
) export_counts
JOIN (
  SELECT load_batch_id, COUNT(*) AS eligible_count
  FROM dwd_amazon_fashion_review
  WHERE load_batch_id='prod_v1_100k'
    AND review_text_clean IS NOT NULL AND TRIM(review_text_clean)<>''
    AND review_key IS NOT NULL AND TRIM(review_key)<>''
    AND rating_label IN ('negative','neutral','positive')
  GROUP BY load_batch_id
) eligible_counts
  ON export_counts.load_batch_id=eligible_counts.load_batch_id;

SELECT
  SUM(CASE WHEN review_key IS NULL OR TRIM(review_key)='' THEN 1 ELSE 0 END) AS null_or_blank_review_key,
  SUM(CASE WHEN review_text_clean IS NULL OR TRIM(review_text_clean)='' THEN 1 ELSE 0 END) AS null_or_blank_review_text,
  SUM(CASE WHEN rating_label IS NULL OR rating_label NOT IN ('negative','neutral','positive') THEN 1 ELSE 0 END) AS invalid_rating_label,
  SUM(CASE WHEN rating IS NULL THEN 1 ELSE 0 END) AS null_rating,
  SUM(CASE WHEN parent_asin IS NULL OR TRIM(parent_asin)='' THEN 1 ELSE 0 END) AS null_or_blank_parent_asin,
  SUM(CASE WHEN main_category IS NULL OR TRIM(main_category)='' THEN 1 ELSE 0 END) AS null_or_blank_main_category,
  SUM(CASE WHEN review_time IS NULL THEN 1 ELSE 0 END) AS null_review_time,
  SUM(CASE WHEN load_batch_id IS NULL OR load_batch_id<>'prod_v1_100k' THEN 1 ELSE 0 END) AS invalid_batch_id
FROM tmp_nlp_input_prod_v1_100k;

SHOW COLUMNS IN review_dw.tmp_nlp_input_prod_v1_100k;
