# Phase C — HDFS and Hive ODS Smoke Test

## Environment

| Item | Verified result |
|---|---|
| Execution date | 2026-07-21 |
| Docker Desktop | 4.81.0 (232925) |
| Docker Engine | 29.6.1 |
| Hive | 2.3.2 |
| HDFS | NameNode responded successfully; smoke files listed successfully |
| HiveServer2 | Healthy; Beeline connected to `jdbc:hive2://localhost:10000/default` |

The container emitted locale, SLF4J multiple-binding and Hive-on-MR deprecation warnings. These warnings did not prevent HDFS or Hive validation.

## Input

- 100 review sample rows from `reviews_sample_100.jsonl`
- 100 metadata sample rows from `meta_sample_100.jsonl`
- Reservoir-sampling seed: 42
- Both sample JSONL files are ignored and untracked.
- No full raw JSONL file was read or uploaded during Phase C.

## Conversion

- Source format: UTF-8 JSONL
- Target format: UTF-8 control-A-delimited text (`0x01`)
- Review output: 100 physical rows and 10 columns
- Metadata output: 100 physical rows and 14 columns
- Nested arrays and objects: compact JSON strings with `ensure_ascii=False`
- Null representation: `\N`
- Embedded control-A, carriage return, line feed and tab characters in strings: replaced with safe spaces
- Generated files remain under ignored `data/processed/phase_c_smoke/`.

## HDFS Locations

- `/data/review_dw/smoke/ods_amazon_fashion_review/ods_review_smoke.txt` — 36.8 KiB
- `/data/review_dw/smoke/ods_amazon_fashion_meta/ods_meta_smoke.txt` — 142.8 KiB

Each directory contained exactly one uploaded smoke data file at final verification.

## Hive Objects

- Database: `review_dw`
- Review external table: `review_dw.ods_amazon_fashion_review_smoke`
- Metadata external table: `review_dw.ods_amazon_fashion_meta_smoke`

Both objects are repeatable smoke-test external tables. The SQL drops and recreates only these two exact smoke tables; it does not alter unrelated tables or databases.

## Validation Results

### Row counts

| Check | Result |
|---|---:|
| Review input rows | 100 |
| Metadata input rows | 100 |
| Converted review rows | 100 |
| Converted metadata rows | 100 |
| Hive review rows | 100 |
| Hive metadata rows | 100 |

### Rating distribution

| Rating | Review count |
|---:|---:|
| 1.0 | 6 |
| 2.0 | 6 |
| 3.0 | 8 |
| 4.0 | 20 |
| 5.0 | 60 |

### Verified purchase distribution

| Value | Review count |
|---|---:|
| `false` | 15 |
| `true` | 85 |

### Parent ASIN and join observations

- Review rows with non-empty `parent_asin`: 100
- Metadata rows with non-empty `parent_asin`: 100
- Matched rows between the two independent 100-row reservoir samples: 0

The zero sample match is an expected coverage limitation of independently sampled review and metadata files. It is not a full-dataset join-rate result and does not indicate a parsing failure.

### Field alignment

- `rating` parsed as `DOUBLE` and produced the expected five rating groups.
- `review_timestamp` is `BIGINT`; all 100 values parsed as non-null.
- `helpful_vote` is `BIGINT`; all 100 values parsed as non-null.
- `verified_purchase` is `BOOLEAN`; all 100 values parsed as non-null.
- Review `asin` and `parent_asin` values were visible in their intended columns.
- Metadata `product_title` and `store_name` were visible; each had 100 parsed non-null values.
- Review text previews remained in the review-text column, so no delimiter-induced column shift was observed.

## Limitations

- Only two 100-row samples were loaded.
- These are smoke-test tables and metrics, not production statistics.
- No full dataset was uploaded to HDFS.
- No production ODS or DWD cleaning was executed.
- No NLP prediction was executed.
- The independent samples did not share a `parent_asin`; a future coordinated sample or larger warehouse load is required for a positive join demonstration.

## Result

**PASS** — both Hive tables returned exactly 100 rows, required types parsed successfully, and field alignment was verified.
