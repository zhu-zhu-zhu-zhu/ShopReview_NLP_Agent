# ShopReview Production Agent

ReviewOps Copilot 使用 DeepSeek 的 OpenAI-compatible API，通过固定白名单工具读取 ShopReview production warehouse 指标，并生成有来源、有范围、有证据的中文风险调查结果。

## 配置

复制 `agent/.env.example` 为被 Git 忽略的 `agent/.env`：

```env
BACKEND_BASE_URL=http://127.0.0.1:8080
HTTP_TIMEOUT_SEC=15
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SEC=60
AGENT_MAX_STEPS=6
AGENT_TEMPERATURE=0.2
```

不得提交 API Key。曾在聊天、截图或日志中暴露的 Key 应在 DeepSeek 控制台轮换。

## 调用链

```text
用户问题
  → POST /api/agent/chat
  → orchestrator
  → DeepSeek 选择白名单工具
  → InProcessAdapter / HttpApiAdapter
  → WarehouseProvider
  → MySQL serving v2（只读）
  → 证据化中文回答
```

FastAPI 内部调用使用 `InProcessAdapter`，避免向同一 uvicorn 进程发起嵌套 HTTP；独立脚本使用 `HttpApiAdapter`。

## 16 个白名单工具

`get_data_health`、`get_kpi`、`get_sentiment_trend`、`get_monthly_sentiment_trend`、`get_top_negative_products`、`get_top_positive_products`、`get_top_negative_stores`、`get_top_positive_stores`、`get_category_sentiment`、`get_verified_purchase_sentiment`、`get_rating_prediction_matrix`、`get_prediction_confidence`、`get_aspect_stats`、`get_negative_reasons`、`get_alerts`、`search_review_samples`。

Agent 无任意 SQL 工具，不提供写库、执行 shell、读取原始 JSONL 或修改生产数据的能力。

## 数据解释纪律

- 数字、比例、排名和趋势必须先调用工具；
- 商品使用 `parent_asin`，店铺使用 `store_key`；
- 方面代码为 `appearance`、`size_fit`、`comfort`、`material`、`price_value`、`quality`、`shipping_packaging`、`durability`；
- 方面与负面原因来自 `keyword_rules_v1`，不是 LLM 抽取；
- 负面原因是全局粒度，不能归因到单个商品或店铺；
- 评论只允许展示 `review_text_preview`；
- 回答应注明工具、来源、数据范围和生产指标标志。

## 运行与验证

Agent 通过 FastAPI 暴露：

```http
POST /api/agent/chat
Content-Type: application/json

{"question":"调查最高风险商品，并给出证据和建议"}
```

连通检查：

```powershell
cd D:\bdt-app-course\projects\ShopReview_NLP_Agent
$env:PYTHONPATH=(Get-Location).Path
.\.venv\Scripts\python.exe -m agent.scripts.ping_kpi
```

预期看到 `DATA_MODE=warehouse`、`review_count=99703`，以及趋势接口成功返回。
