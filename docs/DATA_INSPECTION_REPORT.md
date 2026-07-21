# Amazon Fashion Dataset Inspection Report

> **Sample inspection only — not a complete dataset statistic.**

## 1. Inspection Scope

The first **100,000** review physical lines and first **50,000** metadata physical lines were inspected. Results describe only these bounded leading subsets.

## 2. Source Files

- `Amazon_Fashion.jsonl` (1,051,324,731 bytes)
- `meta_Amazon_Fashion.jsonl` (1,422,365,805 bytes)

## 3. Inspection Method

Python standard-library JSON parsing processed one UTF-8 line at a time. No pandas load, SQLite, HDFS, Hive or NLP model was used. Deterministic reservoir samples use seed 42. Raw files remained read-only.

## 4. Review Subset Summary

- Physical lines inspected: 100,000
- Valid JSON objects: 100,000
- Malformed JSON: 0
- Blank lines: 0
- Missing/null/blank review text: 24
- Timestamp range (UTC): 2003-06-19T23:07:30+00:00 to 2023-03-20T04:33:44.379000+00:00
- Helpful votes: valid=100,000, invalid/missing=0, min=0.0, max=454.0, mean=0.66438
- Verified purchase distribution: boolean:false: 12,814, boolean:true: 87,186

## 5. Metadata Subset Summary

- Physical lines inspected: 50,000
- Valid JSON objects: 50,000
- Malformed JSON: 0
- Blank lines: 0

## 6. Observed Fields

Review: `asin`, `helpful_vote`, `images`, `parent_asin`, `rating`, `text`, `timestamp`, `title`, `user_id`, `verified_purchase`

Metadata: `average_rating`, `bought_together`, `categories`, `description`, `details`, `features`, `images`, `main_category`, `parent_asin`, `price`, `rating_number`, `store`, `title`, `videos`

> Sample inspection only — not a complete dataset statistic.

## 7. Rating and Weak Sentiment Distribution

Ratings: 1: 9,010, 2: 6,673, 3: 10,947, 4: 16,424, 5: 56,946

Rating-based weak labels: negative: 15,683, neutral: 10,947, positive: 73,370

Weak labels are derived from ratings (1–2 negative, 3 neutral, 4–5 positive); they are not NLP predictions.

## 8. Parent ASIN Join Check

Within the two inspected leading subsets, 11,516 of 100,000 review rows with non-empty `parent_asin` matched an inspected metadata `parent_asin`.
Sample join rate: **11.516000%**.
This is not a full-dataset join rate because metadata outside the first bounded subset was not considered.

## 9. Local Sampling

Reservoir sampling generated 100 review objects and 100 metadata objects with seed 42. These real-record JSONL samples are ignored and remain local.

## 10. Warehouse Implications

The observed two-source schema supports separate review and metadata ODS tables, timestamp conversion in DWD, explicit empty-text rules, a `parent_asin` join, nullable metadata handling and rating-based weak-label generation. All Hive types remain Draft pending broader validation.

## 11. Limitations

- Only a bounded leading subset was inspected; every result in this report is a sample statistic.
- Exact full-dataset counts, distinct counts, duplicate counts and join quality will be calculated later with Hive.
- No NLP model was executed.
- No HDFS or Hive work was executed.

## 12. Recommended Next Step

Review this checkpoint with the team, then prepare Draft HDFS landing and ODS schemas without claiming full-dataset statistics.

> **Sample inspection only — not a complete dataset statistic.**
