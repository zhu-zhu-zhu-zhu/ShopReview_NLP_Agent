DROP VIEW IF EXISTS review_dw.vw_dwd_review_with_sentiment_smoke;
DROP TABLE IF EXISTS review_dw.dwd_review_sentiment_contract_smoke;

CREATE TABLE review_dw.dwd_review_sentiment_contract_smoke (
  review_key STRING, pred_label STRING, pred_score DOUBLE, model_version STRING,
  inferred_at TIMESTAMP, prediction_source STRING
)
STORED AS PARQUET;

INSERT OVERWRITE TABLE review_dw.dwd_review_sentiment_contract_smoke
SELECT review_key, rating_label, 1.0, 'contract_smoke_not_a_model',
       current_timestamp, 'synthetic_contract_test'
FROM review_dw.dwd_amazon_fashion_review_smoke;

CREATE VIEW review_dw.vw_dwd_review_with_sentiment_smoke AS
SELECT d.*, p.pred_label, p.pred_score, p.model_version, p.inferred_at, p.prediction_source
FROM review_dw.dwd_amazon_fashion_review_smoke d
LEFT JOIN review_dw.dwd_review_sentiment_contract_smoke p
  ON d.review_key = p.review_key;
