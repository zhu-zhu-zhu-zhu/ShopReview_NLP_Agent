# Rule-based Aspect and Negative-Reason Warehouse Contract

## 1. Contract status

- Batch：`prod_v1_100k`
- Model：`tfidf_logreg_oof_v1`
- Extraction method：`keyword_rules_v1`
- Aspect rule version：`fashion_aspects_v1`
- Negative-reason rule version：`negative_reasons_v1`
- Status：Implemented in serving v2

本模块是确定性关键词规则聚合，不是 DeepSeek、LLM 或独立方面模型抽取。

## 2. Production aspects

| Code | Name | 当前 mentions | 当前 products |
|---|---|---:|---:|
| `appearance` | Appearance | 38,475 | 33,315 |
| `size_fit` | Size & Fit | 35,897 | 31,150 |
| `comfort` | Comfort | 15,838 | 13,969 |
| `material` | Material | 15,041 | 13,714 |
| `price_value` | Price & Value | 14,564 | 12,938 |
| `quality` | Quality | 14,114 | 12,910 |
| `shipping_packaging` | Shipping & Packaging | 3,888 | 3,730 |
| `durability` | Durability | 3,632 | 3,398 |

同一评论可以命中多个方面，因此 mention 总数不能与评论总数直接对账。

## 3. Aspect serving schema

表：`dws_aspect_summary`

| Field | Meaning |
|---|---|
| `aspect_code` / `aspect_name` | 受控方面代码和展示名 |
| `mention_count` | 命中该方面规则的评论数 |
| `product_count` | 涉及商品数 |
| `positive_count` / `neutral_count` / `negative_count` | 使用 OOF 预测标签聚合 |
| `positive_rate` / `neutral_rate` / `negative_rate` | 三类占 mention 的比例 |
| `average_prediction_score` | 命中评论的平均模型置信度 |
| `extraction_method` | `keyword_rules_v1` |
| `rule_version` | `fashion_aspects_v1` |
| `load_batch_id` / `model_version` | 生产范围 |

每个方面内：三类数量之和应等于 `mention_count`，三类比例之和应近似 1。

## 4. Production negative reasons

全局原因代码：

`return_issue`、`wrong_size`、`poor_quality`、`overpriced`、`damaged_item`、`uncomfortable`、`color_mismatch`、`not_as_described`、`delivery_issue`。

表：`dws_negative_reasons`

| Field | Meaning |
|---|---|
| `reason_code` / `reason_name` | 受控原因 |
| `mention_count` | 负面预测评论中的规则命中数 |
| `product_count` | 涉及商品数 |
| `share_of_negative_reviews` | mention / 15,899 |
| `average_prediction_score` | 命中记录平均置信度 |
| `extraction_method` | `keyword_rules_v1` |
| `rule_version` | `negative_reasons_v1` |

原因表是全局粒度，不支持把原因归因到某个 `parent_asin` 或店铺。API 收到商品过滤时返回空列表，防止产生虚假商品级证据。

## 5. Validation rules

- `aspect_code`、`reason_code` 必须属于受控词表；
- 所有 count 必须非负；
- 比例必须在 0～1；
- `load_batch_id` 与 `model_version` 必须匹配生产配置；
- `extraction_method` 与 `rule_version` 必须非空；
- 方面三类数量必须与 mention 对账；
- 规则命中结果不得描述为模型训练标签或 LLM 输出。

## 6. Responsibility boundary

Warehouse 负责规则 SQL、聚合、对账和 MySQL 同步；FastAPI 负责只读参数化查询；Agent 只能解释已返回结果，不得补造规则命中、商品级原因或完整评论。
