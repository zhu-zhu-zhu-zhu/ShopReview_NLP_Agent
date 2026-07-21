CREATE DATABASE IF NOT EXISTS review_dw;

CREATE EXTERNAL TABLE IF NOT EXISTS review_dw.ods_amazon_fashion_review (
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
PARTITIONED BY (load_batch_id STRING)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\001'
STORED AS TEXTFILE
LOCATION '/data/review_dw/ods/amazon_fashion_review'
TBLPROPERTIES ('serialization.null.format'='\N');

ALTER TABLE review_dw.ods_amazon_fashion_review
ADD IF NOT EXISTS PARTITION (load_batch_id='prod_v1_100k')
LOCATION '/data/review_dw/ods/amazon_fashion_review/load_batch_id=prod_v1_100k';

CREATE EXTERNAL TABLE IF NOT EXISTS review_dw.ods_amazon_fashion_meta (
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
PARTITIONED BY (load_batch_id STRING)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\001'
STORED AS TEXTFILE
LOCATION '/data/review_dw/ods/amazon_fashion_meta'
TBLPROPERTIES ('serialization.null.format'='\N');

ALTER TABLE review_dw.ods_amazon_fashion_meta
ADD IF NOT EXISTS PARTITION (load_batch_id='prod_v1_100k')
LOCATION '/data/review_dw/ods/amazon_fashion_meta/load_batch_id=prod_v1_100k';
