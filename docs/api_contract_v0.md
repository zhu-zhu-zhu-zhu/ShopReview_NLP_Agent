# API Contract v0（阶段 G / H 共用）

> **状态：Draft v0.1 — 字段表定稿（冒烟）**  
> **Base URL：** `http://127.0.0.1:8080`  
> **数据模式：** `DATA_MODE=smoke`（读 `exports/agent/smoke/`）；正式版切 `warehouse` 时**路径与字段名尽量不变**  
> **编码：** UTF-8 JSON  
> **对齐导出：** Phase F `schema_version=draft_v0.1`  
> **消费者：** 可视化大屏、Agent 工具（阶段 H）

变更字段或路径前，须同步通知大屏与 Agent 开发；本文件为对接基准。

---

## 1. 通用约定

### 1.1 成功响应包装

所有业务接口（除另有说明）使用：

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "data_mode": "smoke",
    "schema_version": "draft_v0.1",
    "data_scope": "phase_d_e_smoke_contract",
    "production_business_metrics": false,
    "source": "smoke:sentiment_overview.json"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 业务是否成功 |
| `data` | object \| array | 载荷；KPI 为 object，列表类为 array |
| `meta.data_mode` | string | `smoke` \| `warehouse` |
| `meta.schema_version` | string | 与导出一致，当前 `draft_v0.1` |
| `meta.data_scope` | string | 主要数据范围标签；多 scope 时取主数据集或在接口说明中写清 |
| `meta.production_business_metrics` | boolean | smoke 下必须为 `false` |
| `meta.source` | string | 如 `smoke:product_sentiment.json` 或将来的 `warehouse:dws_...` |

### 1.2 失败 / 未实现响应

```json
{
  "ok": false,
  "error": "not_available_in_smoke",
  "message": "当前为 smoke 快照，无日趋势数据",
  "meta": {
    "data_mode": "smoke",
    "schema_version": "draft_v0.1",
    "production_business_metrics": false
  }
}
```

| `error` 建议值 | 含义 |
|----------------|------|
| `not_available_in_smoke` | 冒烟模式无此能力 |
| `not_implemented` | 路由占位未接数仓 |
| `invalid_args` | 参数非法 |
| `upstream_unavailable` | 读文件/仓失败 |

HTTP：未实现可用 **501**；参数错误用 **400**；成功用 **200**（含 `ok:false` 的业务失败也可用 200，前后端按 `ok` 判断亦可，**实现时在 README 写死一种**）。本契约推荐：

- 成功：`200` + `ok:true`
- 参数错误：`400` + `ok:false`
- 冒烟未实现：`501` + `ok:false`
- 服务端读数失败：`500` + `ok:false`

### 1.3 硬性规则

| 规则 | 说明 |
|------|------|
| 商品主键 | 使用 `parent_asin`，**禁止**自造 `product_id` |
| 禁止编造 | 无 `inconsistency_rate` 等 smoke 不存在字段 |
| 隐私 | **禁止**返回 `user_id`、完整未截断长评 |
| 范围诚实 | UI/Agent 必须暴露 `production_business_metrics` 与 `data_scope` |
| Provider | 路由经 Provider；`smoke` / `warehouse` 切换不改 path |

### 1.4 方面受控词（展示可中英对照）

`size` · `color` · `material` · `comfort` · `workmanship` · `description_mismatch` · `packaging` · `delivery` · `price` · `other`

---

## 2. 接口总表

| Method | Path | smoke 来源 | 冒烟 |
|--------|------|------------|------|
| GET | `/api/health` | `manifest.json` | ✅ 必做 |
| GET | `/api/kpi` | `sentiment_overview.json` | ✅ 必做 |
| GET | `/api/top-negative-products` | `product_sentiment.json` | ✅ 必做 |
| GET | `/api/aspects` | `aspect_summary.json` | ✅ 必做 |
| GET | `/api/negative-reasons` | `negative_reasons.json` | ✅ 必做 |
| GET | `/api/trend` | — | ⏸ 占位 |
| GET | `/api/alerts` | — | ⏸ 占位 |
| GET | `/api/samples` | — | ⏸ 占位 |

---

## 3. `GET /api/health`

无查询参数。

### 3.1 响应字段（`data` 可扁平到根，与包装二选一；推荐根级字段如下，便于大屏）

为减少嵌套，**health 允许不套 `data`**，直接：

```json
{
  "ok": true,
  "data_mode": "smoke",
  "schema_version": "draft_v0.1",
  "production_business_metrics": false,
  "export_name": "Phase F warehouse smoke",
  "data_scope_summary": "phase_d_e_smoke_contract + synthetic_aspect_contract_smoke",
  "sentiment_data": "Phase D/E contract smoke",
  "aspect_data": "synthetic contract data",
  "record_counts": {
    "sentiment_overview": 1,
    "product_sentiment": 50,
    "aspect_summary": 16,
    "negative_reasons": 14
  },
  "source": "smoke:manifest.json"
}
```

| 字段 | 类型 | 必填 | 来源 / 说明 |
|------|------|------|-------------|
| `ok` | boolean | ✅ | 固定 true（文件可读时） |
| `data_mode` | string | ✅ | 配置 `DATA_MODE` |
| `schema_version` | string | ✅ | manifest / 导出 |
| `production_business_metrics` | boolean | ✅ | manifest，smoke=`false` |
| `export_name` | string | ✅ | manifest.`export_name` |
| `data_scope_summary` | string | ✅ | 由 sentiment/aspect scope 拼摘要 |
| `sentiment_data` | string | 建议 | manifest |
| `aspect_data` | string | 建议 | manifest |
| `record_counts` | object | 建议 | manifest.`record_counts` |
| `source` | string | ✅ | `smoke:manifest.json` |

---

## 4. `GET /api/kpi`

### 4.1 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_date` | string `YYYY-MM-DD` | 否 | smoke：**忽略**；若传入可在 `meta.message` 说明「当前为快照，不支持时间窗」 |
| `end_date` | string | 否 | 同上；只传一端时返回 `400 invalid_args` |

### 4.2 `data` 字段（来自 overview `records[0]`）

| 字段 | 类型 | 必填 | smoke 对账样例 |
|------|------|------|----------------|
| `review_count` | number | ✅ | `50` |
| `user_count` | number | ✅ | `28` |
| `product_count` | number | ✅ | `50` |
| `positive_count` | number | ✅ | `44` |
| `neutral_count` | number | ✅ | `6` |
| `negative_count` | number | ✅ | `0` |
| `positive_rate` | number | ✅ | `0.88`（0～1） |
| `neutral_rate` | number | ✅ | `0.12` |
| `negative_rate` | number | ✅ | `0.0` |
| `average_rating` | number | ✅ | `4.46` |
| `generated_at` | string | 建议 | 导出时间戳 |
| `data_scope` | string | ✅ | `phase_d_e_smoke_contract` |

`meta.source` = `smoke:sentiment_overview.json`  
`meta.data_scope` = 记录的 `data_scope`

**禁止字段：** `inconsistency_rate`、`total_reviews`（若需别名，仅在文档注明 `total_reviews` 为 `review_count` 的展示别名，响应体仍用 `review_count`）。

---

## 5. `GET /api/top-negative-products`

### 5.1 查询参数

| 参数 | 类型 | 必填 | 默认 | 约束 |
|------|------|------|------|------|
| `limit` | int | 否 | `10` | 1～50，超出则 clamp |
| `min_reviews` | int | 否 | **`1`（smoke）** | ≥0；正式环境建议默认 20 |

### 5.2 排序

1. `negative_rate` 降序  
2. `negative_count` 降序  
3. `review_count` 降序  

过滤：`review_count >= min_reviews`。

### 5.3 `data`：array of object

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `parent_asin` | string | ✅ | 商品族主键 |
| `product_title` | string | ✅ | 可截断展示，接口返回全文即可 |
| `store_name` | string \| null | 建议 | 店铺 |
| `review_count` | number | ✅ | |
| `average_rating` | number | ✅ | |
| `positive_count` | number | ✅ | |
| `neutral_count` | number | ✅ | |
| `negative_count` | number | ✅ | |
| `positive_rate` | number | ✅ | 0～1 |
| `neutral_rate` | number | ✅ | |
| `negative_rate` | number | ✅ | |
| `verified_purchase_rate` | number | 建议 | |
| `average_helpful_vote` | number | 建议 | |
| `generated_at` | string | 建议 | |
| `data_scope` | string | ✅ | |

`meta.source` = `smoke:product_sentiment.json`  
`meta.data_scope` = `phase_d_e_smoke_contract`（与导出一致）

---

## 6. `GET /api/aspects`

### 6.1 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `aspect` | string | 否 | 过滤受控词，如 `size`；非法值 → 空列表或 `400`（推荐空列表 + ok true） |

### 6.2 `data`：array of object

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `aspect` | string | ✅ | 受控英文词 |
| `reason_code` | string | ✅ | |
| `reason_name` | string | ✅ | |
| `mention_count` | number | ✅ | |
| `negative_count` | number | ✅ | |
| `neutral_count` | number | ✅ | |
| `positive_count` | number | ✅ | |
| `negative_rate` | number | ✅ | 0～1 |
| `average_confidence` | number | ✅ | 0～1 |
| `extractor_version` | string | ✅ | 如 `synthetic_contract_smoke_v1` |
| `generated_at` | string | 建议 | |
| `data_scope` | string | ✅ | 多为 `synthetic_aspect_contract_smoke` |

`meta.source` = `smoke:aspect_summary.json`

---

## 7. `GET /api/negative-reasons`

### 7.1 查询参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `limit` | int | 否 | `20` | 1～100，clamp |
| `parent_asin` | string | 否 | — | 按商品过滤 |

### 7.2 排序（建议）

`reason_count` 降序，其次 `reason_share` 降序。

### 7.3 `data`：array of object

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `parent_asin` | string | ✅ | |
| `product_title` | string | ✅ | |
| `aspect` | string | ✅ | |
| `reason_code` | string | ✅ | |
| `reason_name` | string | ✅ | |
| `reason_count` | number | ✅ | |
| `reason_share` | number | ✅ | 0～1，分母为该商品负面方面提及 |
| `extractor_version` | string | ✅ | |
| `generated_at` | string | 建议 | |
| `data_scope` | string | ✅ | |

`meta.source` = `smoke:negative_reasons.json`

---

## 8. 占位接口（冒烟必须诚实失败）

### 8.1 `GET /api/trend`

- 冒烟：`501` + `error=not_available_in_smoke`  
- 正式：日序列字段待 DWS 日表后另开 `api_contract_v0.1+`

### 8.2 `GET /api/alerts`

- 冒烟：同上  
- 正式：告警快照就绪后启用

### 8.3 `GET /api/samples`

- 冒烟：同上（安全导出故意无全文）  
- 正式：仅脱敏截断样例，仍禁止 `user_id`

---

## 9. 与 smoke 文件映射速查

| API | 文件 | 导出 wrapper 字段 |
|-----|------|-------------------|
| health | `manifest.json` | `schema_version`, `export_name`, `production_business_metrics`, `record_counts`, … |
| kpi | `sentiment_overview.json` | `schema_version`, `dataset`, `source_table`, `data_scope`, `records` |
| top-negative-products | `product_sentiment.json` | 同上 |
| aspects | `aspect_summary.json` | 同上 |
| negative-reasons | `negative_reasons.json` | 同上 |

导出文件外层的 `schema_version` / `dataset` / `source_table` **不必**原样塞进 `data`；由 Provider 取 `records`，元信息进 `meta`。

---

## 10. Agent 工具映射（阶段 H 预留）

| Agent 工具名 | HTTP |
|--------------|------|
| `get_kpi` | `GET /api/kpi` |
| `get_top_negative_products` | `GET /api/top-negative-products` |
| `get_aspect_stats` | `GET /api/aspects` |
| `get_negative_reasons` | `GET /api/negative-reasons` |
| `get_sentiment_trend` | `GET /api/trend`（⏸） |
| `get_alerts` | `GET /api/alerts`（⏸） |
| `search_review_samples` | `GET /api/samples`（⏸） |

---

## 11. 版本与变更

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1 | 2026-07-22 | 按 Phase F smoke 字段定稿；供 G 冒烟实现 |

**定稿原则：** 实现 backend 时以本文为准；若发现导出缺字段，先改契约再改代码，并通知大屏/Agent。

---

## 12. 步骤 1 完成标志

- [x] 本文件已创建：`docs/api_contract_v0.md`
- [ ] 组内口头确认（你与数仓/前端）path 与主键 `parent_asin`
- [ ] 步骤 2 起按本文实现 `SmokeJsonProvider` 与路由
