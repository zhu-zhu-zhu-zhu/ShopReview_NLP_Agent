USE review_dw;
SELECT COUNT(*) AS matched_review_ods_count FROM ods_amazon_fashion_review_matched_smoke;
SELECT COUNT(*) AS matched_metadata_ods_count FROM ods_amazon_fashion_meta_matched_smoke;
SELECT COUNT(*) AS inner_join_count FROM ods_amazon_fashion_review_matched_smoke r JOIN ods_amazon_fashion_meta_matched_smoke m ON r.parent_asin=m.parent_asin;
SELECT COUNT(*) AS dwd_count FROM dwd_amazon_fashion_review_smoke;
SELECT COUNT(*) AS blank_clean_text FROM dwd_amazon_fashion_review_smoke WHERE review_text_clean IS NULL OR trim(review_text_clean)='';
SELECT COUNT(*) AS null_review_key FROM dwd_amazon_fashion_review_smoke WHERE review_key IS NULL OR trim(review_key)='';
SELECT COUNT(*) AS duplicate_review_key_groups FROM (SELECT review_key FROM dwd_amazon_fashion_review_smoke GROUP BY review_key HAVING COUNT(*)>1) x;
SELECT rating_label, COUNT(*) AS row_count FROM dwd_amazon_fashion_review_smoke GROUP BY rating_label ORDER BY rating_label;
SELECT COUNT(*) AS invalid_rating_label FROM dwd_amazon_fashion_review_smoke WHERE rating_label NOT IN ('negative','neutral','positive');
SELECT COUNT(product_title) AS product_title_non_null, COUNT(store_name) AS store_non_null, COUNT(main_category) AS category_non_null, COUNT(review_time) AS valid_review_time FROM dwd_amazon_fashion_review_smoke;
SELECT COUNT(*) AS eligible_joined_rows
FROM ods_amazon_fashion_review_matched_smoke r
JOIN ods_amazon_fashion_meta_matched_smoke m ON r.parent_asin=m.parent_asin
WHERE r.review_text IS NOT NULL AND trim(r.review_text)<>'';
SELECT substr(review_key,1,12) AS review_key_prefix, asin, parent_asin, rating, rating_label,
       product_title, store_name, substr(review_text_clean,1,80) AS text_preview
FROM dwd_amazon_fashion_review_smoke LIMIT 10;
