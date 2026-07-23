# ShopReview Production API 参考

## 1. 通用约定

- Base URL：`http://127.0.0.1:8080`
- 数据范围：`load_batch_id=prod_v1_100k`
- 模型版本：`model_version=tfidf_logreg_oof_v1`
- 数据模式：`warehouse`
- schema：`serving_v2`
- 比例字段：0～1，前端负责格式化为百分比
- 商品主键：`parent_asin`
- 店铺主键：`store_key`

普通成功响应：

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "data_mode": "warehouse",
    "schema_version": "serving_v2",
    "data_scope": "prod_v1_100k+tfidf_logreg_oof_v1",
    "production_business_metrics": true,
    "source": "warehouse:dws_sentiment_overview",
    "load_batch_id": "prod_v1_100k",
    "model_version": "tfidf_logreg_oof_v1",
    "serving_release": "prod_v2"
  }
}
```

上游不可用时返回 `ok=false` 和 `error=upstream_unavailable`，不会用零值或 mock 数据伪装成功。

## 2. 健康与 KPI

### `GET /api/health`

返回数据模式、批次、模型、MySQL 来源以及 13 张 serving 表的行数。用于启动检查、Agent 血缘核对和前端状态栏。

当前关键值：

| 字段 | 值 |
|---|---|
| `production_business_metrics` | `true` |
| `data_scope_summary` | `prod_v1_100k+tfidf_logreg_oof_v1` |
| `source` | `mysql:shopreview_serving` |
| `review_count` | 99,703 |

### `GET /api/kpi`

返回 `review_count`、`product_count`、正中负数量和比例、`average_rating`、`average_prediction_score`、批次与模型。

## 3. 时间趋势

### `GET /api/trend`

参数：

| 参数 | 类型 | 规则 |
|---|---|---|
| `start_date` | `YYYY-MM-DD` | 与 `end_date` 同时提供 |
| `end_date` | `YYYY-MM-DD` | 与 `start_date` 同时提供 |
| `limit` | int | 1～5000 |
| `recent_days` | int | 1～5000，返回最新 N 个日期行并按时间升序 |

字段包括 `dt`、评论量、正中负数量和比例、平均评分。

### `GET /api/trends/monthly`

返回全部 200 个月度行，按 `month_id` 升序。字段还包括商品数和平均预测置信度。

## 4. 商品与店铺排行榜

### `GET /api/top-negative-products`

- `limit`：默认 10，限制为 1～50；
- `min_reviews`：默认 1，必须大于等于 0；
- 排序：`negative_rate DESC, negative_count DESC, review_count DESC`。

### `GET /api/top-positive-products`

- `limit`：默认 10，限制为 1～50；
- `min_reviews`：默认 5；
- 排序：`positive_rate DESC, positive_count DESC, review_count DESC`。

商品字段：`parent_asin`、商品标题、店铺、主类目、评论量、平均评分、正中负指标和平均预测置信度。

### `GET /api/stores`

- `limit`：默认 10，1～50；
- `min_reviews`：默认 20；
- 排序：负面率、负面数、评论数降序。

### `GET /api/top-positive-stores`

- `limit`：默认 10，1～50；
- `min_reviews`：默认 20；
- 排序：正面率、正面数、评论数降序。

店铺字段：`store_key`、`store_name`、评论数、商品数、平均评分、正中负指标和平均预测置信度。

## 5. 业务分析接口

| Path | 数据表 | 粒度与说明 |
|---|---|---|
| `/api/categories` | `dws_category_sentiment` | 主类目；当前 1 行 |
| `/api/verified-purchase` | `dws_verified_purchase_sentiment` | verified/unverified；2 行 |
| `/api/rating-matrix` | `dws_rating_prediction_matrix` | 5 个星级 × 3 个预测标签；15 行 |
| `/api/confidence` | `dws_prediction_confidence` | low/medium/high/very_high；4 行 |
| `/api/aspects` | `dws_aspect_summary` | 8 个规则方面 |
| `/api/negative-reasons` | `dws_negative_reasons` | 9 个全局负面原因 |
| `/api/alerts` | `dws_sentiment_alerts` | 风险告警；当前 179 行 |
| `/api/samples` | `dws_review_samples` | 脱敏评论预览；当前 150 行 |

`/api/aspects` 可传 `aspect`。合法生产代码为：

`appearance`、`size_fit`、`comfort`、`material`、`price_value`、`quality`、`shipping_packaging`、`durability`。

`/api/negative-reasons` 的生产粒度是全局 `reason_code`，不能用于商品级归因。传入 `parent_asin` 时返回空列表，以避免错误归因。

`/api/alerts` 支持 `limit` 与 `alert_level`；等级为 CRITICAL、HIGH、MEDIUM、LOW。

`/api/samples` 支持 `limit` 与 `pred_label`，只返回 `review_text_preview`，不返回用户标识或完整评论。

## 6. Agent

### `POST /api/agent/chat`

请求：

```json
{
  "question": "调查最高风险店铺，并说明证据",
  "session_id": "optional-session-id"
}
```

`question` 不能为空。Agent 通过白名单工具查询同一套 production API，回答中包含调查步骤、来源与数据范围。LLM Key 缺失或上游失败时返回明确错误，不生成伪造指标。

## 7. 参数化和安全

- 值参数使用 `%(... )s` 绑定，不拼接用户值；
- 表名来自 `_V2_TABLES` 固定白名单；
- `limit`、日期、标签和阈值参数均在路由或工具层校验；
- 所有业务查询只读；
- 应用账号为 `agent_reader`；
- API 响应不包含数据库密码、LLM Key 或 `user_id`。
