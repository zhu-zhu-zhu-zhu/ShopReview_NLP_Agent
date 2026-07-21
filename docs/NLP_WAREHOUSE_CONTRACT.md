# NLP–Warehouse Data Contract

## Version

Draft v0.1

## Warehouse Input to NLP

| Field | Type | Requirement |
|---|---|---|
| `review_key` | string | Required and unique |
| `review_text_clean` | string | Required and non-empty |
| `rating_label` | enum | `negative`, `neutral`, or `positive` |
| `rating` | number | Optional |
| `parent_asin` | string | Optional |
| `main_category` | string | Optional |

`rating_label` is a weak label derived from star rating. It is not a model prediction.

`review_key` is lowercase hexadecimal SHA-256 over the UTF-8 encoding of:

```text
user_id + "|#|" + asin + "|#|" + parent_asin + "|#|" + timestamp + "|#|" + title + "|#|" + text
```

Missing values become empty strings. Meaningful title and review text are not trimmed before key generation.

## NLP Prediction Output

Required fields:

- `review_key`: string
- `pred_label`: `negative|neutral|positive`
- `pred_score`: decimal between 0 and 1
- `model_version`: string
- `inferred_at`: UTC timestamp

Optional fields:

- `negative_score`
- `neutral_score`
- `positive_score`

## Write-back Rules

- `review_key` must exist in DWD.
- There must be one prediction per `review_key` per `model_version`.
- `pred_label` must be valid.
- `pred_score` must be between 0 and 1.
- Unknown review keys must be rejected or quarantined.
- Duplicate prediction keys must be reported.
- `model_version` is mandatory.
- Schema changes require team confirmation.

## Responsibility Boundary

Warehouse responsibilities:

- produce cleaned DWD input;
- validate keys and labels;
- import predictions;
- reconcile prediction counts.

NLP developer responsibilities:

- train and evaluate models;
- return predictions using this contract;
- supply model metrics and `model_version`;
- not change Hive schemas independently.

The Phase E smoke records use `model_version='contract_smoke_not_a_model'` and `prediction_source='synthetic_contract_test'`. They are synthetic interface-test records, not model predictions.

## Production-v1 Handoff

- Batch ID: `prod_v1_100k`
- Source table: `review_dw.dwd_amazon_fashion_review`
- Exported input filename: `nlp_input_prod_v1.jsonl`
- Input fields, in fixed order: `review_key`, `review_text_clean`, `rating_label`, `rating`, `parent_asin`, `main_category`, `review_time`, `load_batch_id`
- Expected prediction output fields: `review_key`, `pred_label`, `pred_score`, `model_version`, `inferred_at`

The NLP developer must preserve `review_key` exactly and must not regenerate, normalize, or otherwise modify it. Every returned prediction must include a non-empty `model_version`; warehouse write-back uniqueness is one row per (`review_key`, `model_version`). A new trained artifact or inference run must use an appropriately versioned `model_version` so results remain distinguishable and auditable.

`rating_label` remains a rating-derived weak supervision label and is not a model prediction. No real production-v1 model predictions have been imported yet.
