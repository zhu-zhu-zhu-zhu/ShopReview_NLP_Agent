# ShopReview 最终生产系统验收报告

## 1. 验收范围

本报告覆盖 `prod_v1_100k` 的 ODS、DWD、NLP、OOF 预测、DWS、MySQL serving v2、FastAPI、大屏和 Agent。本项目是 Amazon Fashion 的正式实验子集，不代表完整公开数据集统计。

## 2. 数据链路对账

| 环节 | 行数或结果 | 状态 |
|---|---:|---|
| ODS 评论 | 100,000 | PASS |
| ODS 元数据 | 76,802 | PASS |
| 空白评论过滤 | 24 | PASS |
| 重复评论去除 | 273 | PASS |
| DWD 评论 | 99,703 | PASS |
| NLP 输入 | 99,703 | PASS |
| OOF 预测 | 99,703 | PASS |
| OOF 唯一键 | 99,703 | PASS |
| OOF 缺失/未知/重复键 | 0 / 0 / 0 | PASS |
| OOF 覆盖率 | 100% | PASS |
| MySQL KPI `review_count` | 99,703 | PASS |

对账公式：`100,000 - 24 - 273 = 99,703`。

## 3. NLP 验收

- 模型：TF-IDF + Logistic Regression；
- 选择参数：`C=0.5`、`class_weight=balanced`；
- 参数选择仅使用训练集和验证集；
- 独立测试集只评估一次；
- 测试 accuracy：0.830408；
- 测试 macro-F1：0.606527；
- 测试 weighted-F1：0.810371；
- 正式数仓预测：5 折 Stratified OOF，`shuffle=True`、`random_state=42`；
- 正式模型版本：`tfidf_logreg_oof_v1`；
- 全量模型 `tfidf_logreg_v1.joblib` 仅用于未来未见评论，没有生成本批 OOF。

OOF 预测分布：

| 标签 | 数量 | 占比 |
|---|---:|---:|
| positive | 64,861 | 65.05% |
| neutral | 18,943 | 19.00% |
| negative | 15,899 | 15.95% |

## 4. serving v2 验收

| MySQL 表 | 当前行数 |
|---|---:|
| `dws_sentiment_overview` | 1 |
| `dws_sentiment_daily` | 4,137 |
| `dws_product_sentiment` | 76,784 |
| `dws_category_sentiment` | 1 |
| `dws_store_sentiment` | 24,269 |
| `dws_verified_purchase_sentiment` | 2 |
| `dws_rating_prediction_matrix` | 15 |
| `dws_prediction_confidence` | 4 |
| `dws_monthly_sentiment` | 200 |
| `dws_sentiment_alerts` | 179 |
| `dws_review_samples` | 150 |
| `dws_aspect_summary` | 8 |
| `dws_negative_reasons` | 9 |

所有表均按 `load_batch_id` 与 `model_version` 查询。原有表未被 API 写入，FastAPI 使用只读账号访问。

## 5. API 与大屏验收

- `/docs`：HTTP 200；
- `/api/health`：HTTP 200，`data_mode=warehouse`；
- `/api/kpi`：HTTP 200，`review_count=99703`；
- 店铺好评榜：HTTP 200，`limit` 与 `min_reviews` 生效；
- 商品好评榜：HTTP 200，`limit` 与 `min_reviews` 生效；
- 原店铺/商品差评榜保留；
- 前端 `npm run build`：PASS；
- 页面指标来自真实 API，无 mock 回退；
- 好评使用青绿色、差评使用洋红色；
- Agent 启动器可拖动，抽屉打开后隐藏；
- 图表支持布局适配和 reduced-motion。

Vite 当前仅报告主 JS chunk 超过 500 kB 的性能建议，不影响构建成功。

## 6. Agent 验收

- 注册 16 个只读白名单工具；
- 可查询 KPI、趋势、排名、告警、品类、认证购买、矩阵、置信度、方面、原因和脱敏样例；
- FastAPI 内采用 in-process provider，避免自身嵌套 HTTP；
- 不提供任意 SQL、写库、shell 或原始文件工具；
- 系统提示词要求先取数再回答；
- 明确区分商品、店铺与全局证据；
- 方面和负面原因明确标注为 `keyword_rules_v1`。

## 7. Git 与敏感信息

- `.env`、`.env.*.local`、模型、JSONL、原始数据、样本和构建物均被忽略；
- 被跟踪 JSONL、`data/raw/*`、`data/sample/*`、模型文件数量均为 0；
- 未发现被跟踪的长格式 `sk-` API Key；
- `backend/.env` 和 `agent/.env` 未提交；
- 生产裁剪删除阶段运行器、合成表、旧导出和相应夹具。

## 8. 已知限制

- production-v1 是 100,000 评论范围，不是完整 Amazon Fashion；
- 训练目标是星级映射弱标签，不是人工真值；
- neutral 类测试 F1 较低，需要谨慎解释；
- Logistic Regression 在 10 个拟合阶段达到 `max_iter=1000`，报告已保留收敛警告；
- 规则方面和负面原因可能一条评论命中多个规则，mention 数不能与评论数直接一一对应；
- Agent 建议是只读分析结果，不代表已执行运营动作。

## 9. 结论

数据、模型、预测、serving、API、大屏和 Agent 已形成闭环；关键行数、键覆盖、模型版本和 MySQL KPI 对账一致。最终生产裁剪后的代码不再依赖阶段数据回退。

PRODUCTION DATA PIPELINE RESULT: PASS

OOF PREDICTION RESULT: PASS

MYSQL SERVING V2 RESULT: PASS

API AND DASHBOARD RESULT: PASS

PRODUCTION AGENT RESULT: PASS
