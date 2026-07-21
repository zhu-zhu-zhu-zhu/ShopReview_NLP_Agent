# Aspect Analysis–Warehouse Data Contract

## Version

Draft v0.1

## Agent/NLP Aspect Input

Each returned aspect row must contain:

| Field | Type | Requirement |
|---|---|---|
| `review_key` | string | Required; must exist in warehouse DWD |
| `aspect` | string | Required; allowed draft value |
| `reason_code` | string | Required |
| `reason_name` | string | Required |
| `aspect_sentiment` | enum | `negative`, `neutral`, or `positive` |
| `confidence` | decimal | Required; inclusive range 0–1 |
| `extractor_version` | string | Required |
| `extracted_at` | UTC timestamp | Required |

Allowed draft fashion aspects are `size`, `color`, `material`, `comfort`, `workmanship`, `description_mismatch`, `packaging`, `delivery`, `price`, and `other`.

## Write-back Rules

- `review_key` must exist in the DWD review table.
- Multiple aspects per `review_key` are allowed.
- Duplicate `(review_key, aspect, reason_code, extractor_version)` rows are not allowed.
- `confidence` must be between 0 and 1 inclusive.
- `aspect_sentiment` must be valid.
- Unknown review keys must be rejected or quarantined.
- `extractor_version` is mandatory.
- Schema or controlled-vocabulary changes require team confirmation.

## Responsibility Boundary

Agent/NLP member responsibilities:

- manage the API key outside the warehouse module;
- call the LLM or aspect model;
- manage prompts, retries, and rate limits;
- return structured aspect results conforming to this contract.

Warehouse developer responsibilities:

- validate the returned schema and controlled values;
- import valid aspect results into Hive;
- build aspect DWD/DWS tables;
- reconcile keys, rows, and aggregate counts;
- export safe aggregate results for downstream use.

No API key is required or stored inside the warehouse module.

The Phase F fixture uses `extractor_version='synthetic_contract_smoke_v1'` and `result_source='synthetic_contract_test'`. It is an interface-test fixture, not an LLM result, model result, or real business statistic.
