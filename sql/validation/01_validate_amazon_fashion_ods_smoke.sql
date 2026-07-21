USE review_dw;

SELECT COUNT(*) AS review_count
FROM ods_amazon_fashion_review_smoke;

SELECT COUNT(*) AS metadata_count
FROM ods_amazon_fashion_meta_smoke;

SELECT rating, COUNT(*) AS review_count
FROM ods_amazon_fashion_review_smoke
GROUP BY rating
ORDER BY rating;

SELECT verified_purchase, COUNT(*) AS review_count
FROM ods_amazon_fashion_review_smoke
GROUP BY verified_purchase;

SELECT COUNT(*) AS review_rows_with_parent_asin
FROM ods_amazon_fashion_review_smoke
WHERE parent_asin IS NOT NULL
  AND TRIM(parent_asin) <> '';

SELECT COUNT(*) AS metadata_rows_with_parent_asin
FROM ods_amazon_fashion_meta_smoke
WHERE parent_asin IS NOT NULL
  AND TRIM(parent_asin) <> '';

SELECT r.parent_asin, r.asin, r.rating, m.product_title, m.store_name
FROM ods_amazon_fashion_review_smoke r
LEFT JOIN ods_amazon_fashion_meta_smoke m
    ON r.parent_asin = m.parent_asin
LIMIT 10;

SELECT COUNT(*) AS matched_sample_rows
FROM ods_amazon_fashion_review_smoke r
INNER JOIN ods_amazon_fashion_meta_smoke m
    ON r.parent_asin = m.parent_asin;

SELECT parent_asin, product_title, store_name
FROM ods_amazon_fashion_meta_smoke
LIMIT 10;

SELECT rating, asin, parent_asin,
       SUBSTR(review_text, 1, 80) AS review_text_preview
FROM ods_amazon_fashion_review_smoke
LIMIT 10;
