# Phase D/E Amazon Fashion Smoke Report

All figures below describe a bounded coordinated smoke sample only. They are not full-dataset statistics.

## Phase D

- Source bounds: at most 50,000 valid metadata objects and 100,000 valid review objects.
- Actual source scan: 50,000 metadata objects and 524 review objects; malformed/non-object records: 0 and 0.
- Target and actual coordinated pairs: 50 and 50 unique `parent_asin` pairs, using the first valid occurrence.
- HDFS paths: `/data/review_dw/smoke_d/ods_review_matched` and `/data/review_dw/smoke_d/ods_meta_matched`.
- Matched ODS tables: `review_dw.ods_amazon_fashion_review_matched_smoke` and `review_dw.ods_amazon_fashion_meta_matched_smoke`.
- Matched review ODS rows: 50; matched metadata ODS rows: 50; INNER JOIN rows: 50.
- DWD table: `review_dw.dwd_amazon_fashion_review_smoke`; row count: 50.
- Empty review rows filtered: 0; eligible joined rows: 50; DWD reconciliation: 50 = 50, PASS.
- Weak-label distribution: negative 0, neutral 6, positive 44; invalid labels: 0. These are rating-derived weak labels, not predictions.
- Timestamp conversion: 50 of 50 DWD rows produced non-null `review_time`; `dt` uses `yyyy-MM-dd`.
- Review-key validation: 0 null/blank keys and 0 duplicate-key groups. The local NLP input and Hive DWD each contain 50 unique keys, with no set differences.
- Metadata enrichment: `product_title`, `store_name`, and `main_category` are non-null in 50 of 50 rows each.

The stable key is lowercase hexadecimal SHA-256 over the UTF-8 encoding of `user_id|#|asin|#|parent_asin|#|timestamp|#|title|#|text`, with missing values represented by empty strings and without trimming meaningful source text before hashing. No source user IDs or complete review texts are shown here.

## Phase E Warehouse Handoff

- Local ignored NLP input: `data/processed/phase_d_e_smoke/nlp_input_smoke.jsonl`.
- NLP input rows: 50. Required fields are `review_key`, `review_text_clean`, and `rating_label`; optional smoke fields are `rating`, `parent_asin`, and `main_category`. `user_id` is excluded.
- Prediction output contract: `review_key`, `pred_label`, `pred_score`, `model_version`, and `inferred_at`, with optional per-class scores.
- Synthetic contract table: `review_dw.dwd_review_sentiment_contract_smoke`; row count: 50.
- Joined view: `review_dw.vw_dwd_review_with_sentiment_smoke`; row count: 50.
- Contract validation: missing predictions 0, unknown prediction keys 0, duplicate `(review_key, model_version)` groups 0, invalid labels 0, invalid scores 0, and missing model versions 0.

The contract rows use `model_version='contract_smoke_not_a_model'` and `prediction_source='synthetic_contract_test'`. They are synthetic interface-test records. No NLP model was trained or executed, and these rows are not model predictions.

## Tests

`python -m unittest tests.data.test_prepare_phase_d_e_smoke -v` passes 5 of 5 test methods. The synthetic temporary cases cover matched and unmatched selection, unique `parent_asin` handling, deterministic/change-sensitive review keys, text cleaning, weak labels, NLP schema privacy, and exact control-A column counts.

## Limitations

- Only a bounded coordinated sample was processed; no full production ODS or DWD load was performed.
- Rating-derived labels are weak labels and are not ground-truth sentiment or model output.
- Synthetic prediction-contract rows test only the write-back interface.
- No actual NLP training, actual model prediction import, DWS, API, dashboard, or Agent integration was performed.

## Result

PHASE D TECHNICAL RESULT: PASS

PHASE E CONTRACT RESULT: PASS
