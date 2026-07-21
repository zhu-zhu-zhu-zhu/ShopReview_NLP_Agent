USE review_dw;

CREATE EXTERNAL TABLE IF NOT EXISTS review_dw.stg_nlp_predictions (
  review_key STRING,
  pred_label STRING,
  pred_score DOUBLE,
  negative_score DOUBLE,
  neutral_score DOUBLE,
  positive_score DOUBLE,
  model_version STRING,
  inferred_at TIMESTAMP
)
PARTITIONED BY (load_batch_id STRING)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\001'
STORED AS TEXTFILE
LOCATION '/data/review_dw/staging/nlp_predictions'
TBLPROPERTIES ('serialization.null.format'='\N');

CREATE TABLE IF NOT EXISTS review_dw.dwd_review_sentiment (
  review_key STRING,
  pred_label STRING,
  pred_score DOUBLE,
  negative_score DOUBLE,
  neutral_score DOUBLE,
  positive_score DOUBLE,
  model_version STRING,
  inferred_at TIMESTAMP,
  imported_at TIMESTAMP
)
PARTITIONED BY (
  load_batch_id STRING,
  model_version_partition STRING
)
STORED AS PARQUET;
