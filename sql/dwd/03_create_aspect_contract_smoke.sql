USE review_dw;

DROP TABLE IF EXISTS stg_review_aspect_contract_smoke;
CREATE TABLE stg_review_aspect_contract_smoke (
  review_key STRING,
  aspect STRING,
  reason_code STRING,
  reason_name STRING,
  aspect_sentiment STRING,
  confidence DOUBLE,
  extractor_version STRING,
  extracted_at_raw STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\001'
STORED AS TEXTFILE
TBLPROPERTIES ('serialization.null.format'='\N');

LOAD DATA LOCAL INPATH '${hiveconf:phase_f_aspect_input}'
OVERWRITE INTO TABLE stg_review_aspect_contract_smoke;

DROP TABLE IF EXISTS dwd_review_aspect_contract_smoke;
CREATE TABLE dwd_review_aspect_contract_smoke (
  review_key STRING,
  aspect STRING,
  reason_code STRING,
  reason_name STRING,
  aspect_sentiment STRING,
  confidence DOUBLE,
  extractor_version STRING,
  extracted_at TIMESTAMP,
  result_source STRING
)
STORED AS PARQUET;

INSERT OVERWRITE TABLE dwd_review_aspect_contract_smoke
SELECT
  review_key,
  aspect,
  reason_code,
  reason_name,
  aspect_sentiment,
  confidence,
  extractor_version,
  CAST(regexp_replace(regexp_replace(extracted_at_raw, 'T', ' '), 'Z', '') AS TIMESTAMP),
  'synthetic_contract_test'
FROM stg_review_aspect_contract_smoke;

DROP TABLE stg_review_aspect_contract_smoke;
