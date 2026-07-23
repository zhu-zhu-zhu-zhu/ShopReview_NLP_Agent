# MySQL Serving v2 Table Manifest

- Batch: `prod_v1_100k`
- Model version: `tfidf_logreg_oof_v1`
- Reconciliation: `PASS`

| Table | Primary key | Grain | Important fields | Hive rows | MySQL rows | Source type | Dashboard/API use |
|---|---|---|---|---:|---:|---|---|
| `dws_sentiment_overview` | load_batch_id + model_version | batch + model | review_count, positive/neutral/negative_count | 1 | 1 | production Hive DWS v1 | KPI overview; `/api/overview` |
| `dws_sentiment_daily` | dt + load_batch_id + model_version | day + batch + model | dt, review_count, sentiment rates | 4137 | 4137 | production Hive DWS v1 | daily trend; `/api/trends/daily` |
| `dws_product_sentiment` | parent_asin + load_batch_id + model_version | product + batch + model | parent_asin, product_title, review_count, negative_rate | 76784 | 76784 | production Hive DWS v1 | product ranking; `/api/products` |
| `dws_category_sentiment` | category_key + load_batch_id + model_version | category + batch + model | main_category, review_count, sentiment rates | 1 | 1 | production Hive DWS v2 aggregate | category comparison; `/api/categories` |
| `dws_store_sentiment` | store_key + load_batch_id + model_version | store + batch + model | store_name, review_count, negative_rate | 24269 | 24269 | production Hive DWS v2 aggregate | store ranking; `/api/stores` |
| `dws_verified_purchase_sentiment` | purchase_status + load_batch_id + model_version | purchase status + batch + model | purchase_status, review_count, sentiment rates | 2 | 2 | production Hive DWS v2 aggregate | purchase comparison; `/api/verified-purchase` |
| `dws_rating_prediction_matrix` | rating_value + pred_label + load_batch_id + model_version | rating + prediction + batch + model | rating_value, pred_label, rate_within_rating | 15 | 15 | production Hive DWS v2 aggregate | rating heatmap; `/api/rating-matrix` |
| `dws_prediction_confidence` | bucket_code + load_batch_id + model_version | confidence bucket + batch + model | bucket_code, review_count, average_prediction_score | 4 | 4 | production Hive DWS v2 aggregate | confidence distribution; `/api/confidence` |
| `dws_monthly_sentiment` | month_id + load_batch_id + model_version | month + batch + model | month_id, review_count, sentiment rates | 200 | 200 | production Hive DWS v2 aggregate | monthly trend; `/api/trends/monthly` |
| `dws_sentiment_alerts` | alert_id | alert | alert_type, alert_level, metric_value, threshold_value | 179 | 179 | production Hive DWS v2 aggregate | risk alerts; `/api/alerts` |
| `dws_review_samples` | sample_id + load_batch_id + model_version | safe sample + batch + model | pred_label, pred_score, review_text_preview | 150 | 150 | bounded sanitized real-data preview | representative cards; `/api/samples` |
| `dws_aspect_summary` | aspect_code + load_batch_id + model_version | aspect + batch + model | aspect_code, mention_count, sentiment rates, rule_version | 8 | 8 | deterministic keyword_rules_v1 | keyword-rule aspects; `/api/aspects` |
| `dws_negative_reasons` | reason_code + load_batch_id + model_version | reason + batch + model | reason_code, mention_count, share_of_negative_reviews, rule_version | 9 | 9 | deterministic keyword_rules_v1 | keyword-rule negative reasons; `/api/negative-reasons` |

## Rule-based tables

`dws_aspect_summary` uses `extraction_method=keyword_rules_v1` and `rule_version=fashion_aspects_v1`.
`dws_negative_reasons` uses `extraction_method=keyword_rules_v1` and `rule_version=negative_reasons_v1`.
These are deterministic keyword-rule results, not LLM, BERT, or learned aspect-model outputs.
