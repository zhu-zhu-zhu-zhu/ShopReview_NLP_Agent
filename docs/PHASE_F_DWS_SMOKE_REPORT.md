# Phase F — Aspect and Topic DWS Smoke Report

All results in this report are smoke-test evidence, not production business metrics.

## Input

- Phase D/E DWD source: `review_dw.dwd_amazon_fashion_review_smoke`, 50 rows.
- Sentiment contract source: `review_dw.dwd_review_sentiment_contract_smoke`, 50 synthetic interface-test rows.
- Synthetic aspect contract: `review_dw.dwd_review_aspect_contract_smoke`, 20 rows covering 15 existing DWD `review_key` values.
- Aspect fixture version: `synthetic_contract_smoke_v1`; result source: `synthetic_contract_test`.

The aspect fixture contains no review text or user identifier. It is not an LLM result, model result, or real business statistic.

## DWS Objects

| Hive table | Grain | Rows | Data scope |
|---|---|---:|---|
| `review_dw.dws_sentiment_overview_smoke` | One overall summary | 1 | `phase_d_e_smoke_contract` |
| `review_dw.dws_product_sentiment_smoke` | Product, title, and store | 50 | `phase_d_e_smoke_contract` |
| `review_dw.dws_aspect_summary_smoke` | Aspect and reason | 16 | `synthetic_aspect_contract_smoke` |
| `review_dw.dws_negative_reason_smoke` | Product and negative reason | 14 | `synthetic_aspect_contract_smoke` |

## Validation Results

### Sentiment overview reconciliation

- Overview rows: 1.
- Prediction-view rows and overview `review_count`: 50 and 50.
- Sentiment count sum: positive 44 + neutral 6 + negative 0 = 50.
- Overview rates: positive 0.88, neutral 0.12, negative 0.00; out-of-range rows: 0.
- Average rating: 4.46. These sentiment values come from the Phase D/E synthetic prediction contract and are not real model predictions.

### Product reconciliation

- Product DWS rows: 50.
- Sum of product `review_count`: 50, equal to overview `review_count`.
- Invalid sentiment or verified-purchase rate rows: 0.
- All rate expressions explicitly protect against division by zero.

### Aspect validation

- Contract rows and valid DWD key matches: 20 and 20.
- Unknown review keys: 0.
- Duplicate `(review_key, aspect, reason_code, extractor_version)` groups: 0.
- Invalid aspects, invalid aspect labels, invalid confidence values, and missing contract fields: 0 each.
- Aspect summary `mention_count` sum: 20, equal to contract rows.
- Invalid aspect rate or average-confidence rows: 0.

### Negative reason reconciliation

- Negative aspect rows: 14.
- Negative-reason DWS rows: 14; sum of `reason_count`: 14.
- Invalid `reason_share` rows: 0.
- `reason_share` uses the negative-aspect count within each `parent_asin` as its denominator.

All stable integrity, uniqueness, controlled-value, reconciliation, and 0–1 range checks passed. No blocking data-quality finding was observed within this bounded smoke scope.

## Agent Export

The following UTF-8 JSON files are intended for Agent mock-adapter development:

- `exports/agent/smoke/sentiment_overview.json`: wrapper metadata plus 1 overview record.
- `exports/agent/smoke/product_sentiment.json`: wrapper metadata plus 50 product records.
- `exports/agent/smoke/aspect_summary.json`: wrapper metadata plus 16 aspect/reason records.
- `exports/agent/smoke/negative_reasons.json`: wrapper metadata plus 14 product/reason records.
- `exports/agent/smoke/manifest.json`: `draft_v0.1` manifest, source tables, scopes, file list, and record counts.

Every dataset export uses the ordered wrapper fields `schema_version`, `dataset`, `source_table`, `data_scope`, and `records`. JSON parsing, schema/order validation, data-scope validation, and forbidden-field scanning passed. No `user_id`, complete review text, credential, or API-key field is exported.

## Responsibility Boundary

- Warehouse produces and validates DWS aggregates and safe exports.
- Agent consumes the exports through a mock adapter and must preserve the supplied scope and limitation labels.
- Agent/NLP members own API keys, calls to an LLM or aspect model, prompts, retries, rate limits, and real structured aspect results.
- The warehouse module does not require or store API keys.

## Limitations

- This is a minimum Phase F smoke test over the existing 50-row Phase D/E DWD sample.
- Sentiment predictions are synthetic contract-test records copied from rating-derived weak labels.
- Aspect records are synthetic contract-test records.
- No real LLM aspect extraction, model training, or API call was performed.
- No production full-data ODS, DWD, or DWS was created.
- Exported metrics are not production business results and must not be used for operational decisions.

## Result

PHASE F TECHNICAL RESULT: PASS

AGENT EXPORT RESULT: PASS
