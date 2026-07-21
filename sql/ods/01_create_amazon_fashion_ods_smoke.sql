CREATE DATABASE IF NOT EXISTS review_dw;

DROP TABLE IF EXISTS review_dw.ods_amazon_fashion_review_smoke;

CREATE EXTERNAL TABLE IF NOT EXISTS review_dw.ods_amazon_fashion_review_smoke (
    rating DOUBLE,
    title STRING,
    review_text STRING,
    images_json STRING,
    asin STRING,
    parent_asin STRING,
    user_id STRING,
    review_timestamp BIGINT,
    helpful_vote BIGINT,
    verified_purchase BOOLEAN
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\001'
STORED AS TEXTFILE
LOCATION '/data/review_dw/smoke/ods_amazon_fashion_review'
TBLPROPERTIES ('serialization.null.format'='\N');

DROP TABLE IF EXISTS review_dw.ods_amazon_fashion_meta_smoke;

CREATE EXTERNAL TABLE IF NOT EXISTS review_dw.ods_amazon_fashion_meta_smoke (
    main_category STRING,
    product_title STRING,
    average_rating DOUBLE,
    rating_number BIGINT,
    features_json STRING,
    description_json STRING,
    price_raw STRING,
    images_json STRING,
    videos_json STRING,
    store_name STRING,
    categories_json STRING,
    details_json STRING,
    parent_asin STRING,
    bought_together_json STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\001'
STORED AS TEXTFILE
LOCATION '/data/review_dw/smoke/ods_amazon_fashion_meta'
TBLPROPERTIES ('serialization.null.format'='\N');
