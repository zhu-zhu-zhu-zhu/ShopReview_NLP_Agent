USE review_dw;

DROP VIEW IF EXISTS review_dw.vw_dwd_review_with_sentiment;

CREATE VIEW review_dw.vw_dwd_review_with_sentiment AS
SELECT
  d.review_key,
  d.asin,
  d.parent_asin,
  d.rating,
  d.rating_label,
  d.review_time,
  d.dt,
  d.verified_purchase,
  d.helpful_vote,
  d.product_title,
  d.store_name,
  d.main_category,
  p.pred_label,
  p.pred_score,
  p.model_version,
  p.inferred_at,
  d.load_batch_id
FROM review_dw.dwd_amazon_fashion_review d
JOIN review_dw.dwd_review_sentiment p
  ON d.review_key=p.review_key
 AND d.load_batch_id=p.load_batch_id;
