# Amazon Fashion Data Dictionary

> Sample inspection only — not a complete dataset statistic.
> Proposed warehouse names and Hive types are Draft.

| Dataset | Field | Presence | Observed types | Nullable | Meaning | Target | Draft Hive type | Status |
|---|---|---:|---|---|---|---|---|---|
| review | `asin` | 100,000 | string:100000 | No | Amazon item identifier | `asin` | `STRING` | Observed in bounded sample |
| review | `helpful_vote` | 100,000 | integer:100000 | No | Helpful-vote count | `helpful_vote` | `BIGINT` | Observed in bounded sample |
| review | `images` | 100,000 | array:100000 | No | Image information | `images` | `ARRAY<STRING>` | Observed in bounded sample |
| review | `parent_asin` | 100,000 | string:100000 | No | Parent product identifier and join key | `parent_asin` | `STRING` | Observed in bounded sample |
| review | `rating` | 100,000 | number:100000 | No | Review star rating | `rating` | `DOUBLE` | Observed in bounded sample |
| review | `text` | 100,000 | string:100000 | No | Review body text | `text` | `STRING` | Observed in bounded sample |
| review | `timestamp` | 100,000 | integer:100000 | No | Review event timestamp | `timestamp` | `BIGINT` | Observed in bounded sample |
| review | `title` | 100,000 | string:100000 | No | Review or product title | `title` | `STRING` | Observed in bounded sample |
| review | `user_id` | 100,000 | string:100000 | No | Reviewer identifier | `user_id` | `STRING` | Observed in bounded sample |
| review | `verified_purchase` | 100,000 | boolean:100000 | No | Verified-purchase indicator | `verified_purchase` | `BOOLEAN` | Observed in bounded sample |
| metadata | `average_rating` | 50,000 | number:50000 | No | Product average rating | `average_rating` | `DOUBLE` | Observed in bounded sample |
| metadata | `bought_together` | 50,000 | null:50000 | Yes | Frequently bought-together information | `bought_together` | `STRING` | Observed in bounded sample |
| metadata | `categories` | 50,000 | array:50000 | No | Product category hierarchy | `categories` | `ARRAY<STRING>` | Observed in bounded sample |
| metadata | `description` | 50,000 | array:50000 | No | Product description | `description` | `ARRAY<STRING>` | Observed in bounded sample |
| metadata | `details` | 50,000 | object:50000 | No | Product detail attributes | `details` | `STRING` | Observed in bounded sample |
| metadata | `features` | 50,000 | array:50000 | No | Product feature list | `features` | `ARRAY<STRING>` | Observed in bounded sample |
| metadata | `images` | 50,000 | array:50000 | No | Image information | `images` | `ARRAY<STRING>` | Observed in bounded sample |
| metadata | `main_category` | 50,000 | string:50000 | No | Primary product category | `main_category` | `STRING` | Observed in bounded sample |
| metadata | `parent_asin` | 50,000 | string:50000 | No | Parent product identifier and join key | `parent_asin` | `STRING` | Observed in bounded sample |
| metadata | `price` | 50,000 | null:45125, number:4875 | Yes | Product price | `price` | `DOUBLE` | Observed in bounded sample |
| metadata | `rating_number` | 50,000 | integer:50000 | No | Product rating count | `rating_number` | `BIGINT` | Observed in bounded sample |
| metadata | `store` | 50,000 | null:1604, string:48396 | Yes | Store or brand name | `store` | `STRING` | Observed in bounded sample |
| metadata | `title` | 50,000 | string:50000 | No | Review or product title | `title` | `STRING` | Observed in bounded sample |
| metadata | `videos` | 50,000 | array:50000 | No | Video information | `videos` | `ARRAY<STRING>` | Observed in bounded sample |

> Sample inspection only — not a complete dataset statistic.
