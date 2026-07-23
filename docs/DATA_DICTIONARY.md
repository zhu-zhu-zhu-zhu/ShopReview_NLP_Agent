# Amazon Fashion 生产数据字典

> Sample inspection only — not a complete dataset statistic.
> 下方第一部分记录有界原始字段观察；后续部分记录已落地的 production-v1 核心字段。

| Dataset | Field | Presence | Observed types | Nullable | Meaning | Target | Initial inferred Hive type | Status |
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

## Production DWD 核心字段

| 字段 | 类型 | 含义与规则 |
|---|---|---|
| `review_key` | STRING | 稳定 SHA-256 评论键；批次内唯一 |
| `review_text` | STRING | 原始评论文本；仅数仓内部保留 |
| `review_text_clean` | STRING | 清洗后非空文本；NLP 唯一特征 |
| `rating` | DOUBLE | 1～5 星 |
| `rating_label` | STRING | 1–2 negative、3 neutral、4–5 positive |
| `asin` | STRING | Amazon 单品标识 |
| `parent_asin` | STRING | 商品聚合与元数据关联主键 |
| `product_title` | STRING | 商品标题 |
| `store_name` | STRING | 店铺/品牌展示名 |
| `main_category` | STRING | 商品主类目 |
| `review_time` | TIMESTAMP | 毫秒时间戳转换结果 |
| `review_year` | INT | DWD 分区辅助字段 |
| `verified_purchase` | BOOLEAN | 是否认证购买 |
| `helpful_vote` | BIGINT | 有用票数 |
| `metadata_matched` | BOOLEAN | 是否匹配元数据 |
| `load_batch_id` | STRING | 当前为 `prod_v1_100k` |

## NLP prediction 核心字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `review_key` | STRING | 原样继承 DWD |
| `pred_label` | STRING | OOF 模型预测标签 |
| `pred_score` | DOUBLE | 预测标签对应概率 |
| `negative_score` | DOUBLE | negative 概率 |
| `neutral_score` | DOUBLE | neutral 概率 |
| `positive_score` | DOUBLE | positive 概率 |
| `model_version` | STRING | `tfidf_logreg_oof_v1` |
| `inferred_at` | TIMESTAMP | OOF 生成时间 |

## MySQL serving v2 表

| 表 | 粒度 | 主键或关键维度 | 当前行数 |
|---|---|---|---:|
| `dws_sentiment_overview` | 批次+模型 | batch, model | 1 |
| `dws_sentiment_daily` | 日期 | `dt` | 4,137 |
| `dws_product_sentiment` | 商品 | `parent_asin` | 76,784 |
| `dws_category_sentiment` | 类目 | `category_key` | 1 |
| `dws_store_sentiment` | 店铺 | `store_key` | 24,269 |
| `dws_verified_purchase_sentiment` | 购买认证 | `purchase_status` | 2 |
| `dws_rating_prediction_matrix` | 星级×预测 | rating, label | 15 |
| `dws_prediction_confidence` | 置信度桶 | `bucket_code` | 4 |
| `dws_monthly_sentiment` | 月 | `month_id` | 200 |
| `dws_sentiment_alerts` | 告警 | `alert_id` | 179 |
| `dws_review_samples` | 脱敏样例 | `sample_id` | 150 |
| `dws_aspect_summary` | 规则方面 | `aspect_code` | 8 |
| `dws_negative_reasons` | 全局负面原因 | `reason_code` | 9 |

所有 serving 表均带 `load_batch_id` 和 `model_version`，API 查询必须同时过滤二者。比例字段统一使用 0～1 小数。

## 口径区分

- `rating_label`：星级生成的弱监督标签；
- `pred_label`：5 折 OOF 模型预测；
- `pred_score`：模型置信度，不等同于业务事实；
- `positive_rate` 等：由 `pred_label` 聚合；
- `mention_count`：关键词规则命中数，不是 LLM 抽取量；
- `review_text_preview`：服务层脱敏预览，不是完整评论。
