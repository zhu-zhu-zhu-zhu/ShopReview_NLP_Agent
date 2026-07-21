# NLP 真实预测回写与正式 DWS 准备报告

## 一、当前状态

| 项目 | 状态 |
|---|---|
| production DWD | `prod_v1_100k`，99,703 行 |
| production NLP input | 已导出并完成交付验证 |
| 真实预测文件 | 尚未收到 |
| 本次工作 | 仅准备预测导入和正式 DWS 管道代码 |

本次没有导入任何真实或合成预测，也没有创建或填充 production 预测表和 DWS 表。`PrepareOnly` 前后只读快照显示 `stg_nlp_predictions`、`dwd_review_sentiment`、`dws_sentiment_overview`、`dws_sentiment_daily`、`dws_product_sentiment` 均为 `ABSENT`。

## 二、预测结果字段

正式预测文件必须是 UTF-8 JSONL，每行一个 JSON 对象。

必填字段：

| 字段 | 规则 |
|---|---|
| `review_key` | 非空，必须存在于 `prod_v1_100k` DWD，必须原样保留 |
| `pred_label` | 只能为 `negative`、`neutral`、`positive` |
| `pred_score` | 数值，范围为 0–1 |
| `model_version` | 非空，只允许安全的字母、数字、点、下划线和连字符 |
| `inferred_at` | 合法 UTC 时间戳 |

可选字段为 `negative_score`、`neutral_score` 和 `positive_score`；提供时必须是 0–1 的数值。文件不得携带 `review_text`、`user_id`、密钥、凭据、SQL 或未约定字段。

## 三、回写流程

```text
prediction JSONL
  → 流式 schema/字段验证
  → SQLite 精确 review_key 与覆盖率对账
  → control-A Hive 文本原子转换
  → 精确 HDFS staging 版本目录
  → Hive staging 分区
  → dwd_review_sentiment 版本分区
  → vw_dwd_review_with_sentiment
  → production DWS
```

验证器不使用 pandas 全量加载。SQLite 状态文件、预测 JSONL、转换文本和本地转换摘要均位于 Git 忽略目录，不进入版本库。

## 四、版本管理

- `load_batch_id` 标识数仓批次，本任务固定为 `prod_v1_100k`；
- `model_version` 由 NLP 成员提供，必须在文件内保持一致；
- `model_version_partition` 由安全化模型版本和 SHA-256 前缀确定，用于避免不同原始版本发生分区碰撞；
- 正式预测表以 `load_batch_id + model_version_partition` 分区；
- 默认禁止覆盖已存在的同批次、同模型版本；只有明确提供 `-ForceSameVersion` 才允许覆盖该精确分区；
- 任一版本操作都不能覆盖或删除其他模型版本。

## 五、质量验证

已准备的自动检查包括：

- JSON 语法、必填字段和禁止字段；
- 标签域、主分数及可选类别分数范围；
- UTC 推理时间；
- `(review_key, model_version)` 唯一性；
- DWD 未知键、缺失键和精确覆盖率；
- 预期模型版本一致性及模型版本分布；
- staging、生产预测表和 joined view 行数对账；
- 预测标签分布及分数最小值、最大值、均值；
- DWS 总览、日粒度、商品粒度的行数与标签和对账；
- 所有比率保持在 0–1；
- 排除 smoke、synthetic 和 contract 测试版本。

合成单元测试共 15 项，覆盖合法记录、畸形 JSON、缺失键、非法标签/分数、重复键、空模型版本、非法时间、禁止字段、全量/部分覆盖率、control-A 确定性、可选分数和安全摘要，结果为 15/15 PASS。

## 六、正式 DWS

| 表 | 粒度 |
|---|---|
| `review_dw.dws_sentiment_overview` | `load_batch_id + model_version` |
| `review_dw.dws_sentiment_daily` | `dt + load_batch_id + model_version` |
| `review_dw.dws_product_sentiment` | `parent_asin + load_batch_id + model_version` |

DWS SQL 只读取 `vw_dwd_review_with_sentiment` 中的真实 `pred_label`，不使用 `rating_label` 代替模型预测，并对除零进行保护。本轮仅准备 SQL，未执行建表或聚合写入。

## 七、责任边界

数仓成员负责：

- 验证真实预测文件；
- 对账并导入预测；
- 保护批次与模型版本；
- 建设 joined view 和正式 DWS；
- 输出导入及聚合验收结果。

NLP 成员负责：

- 训练和评估模型；
- 原样保留 `review_key`；
- 返回真实预测；
- 提供明确的 `model_version` 和模型指标。

## 八、限制

- 尚未收到真实预测文件；
- 尚未导入任何 production 预测；
- 尚未创建或填充 production DWS；
- 没有将弱标签或合成数据写入 production 预测表；
- SQL、正常导入模式和 DWS 模式需在真实预测到达后才可执行验收。

## 九、下一步

等待 NLP 开发者提供真实预测 JSONL 和模型版本，然后运行：

```powershell
.\scripts\run_nlp_prediction_import_production_v1.ps1 `
  -PredictionPath 'D:\path\to\real_predictions.jsonl' `
  -ModelVersion 'real_model_version' `
  -BatchId 'prod_v1_100k' `
  -MinimumCoverage 1.0 `
  -BuildDws
```

首次导入不要使用 `-ForceSameVersion`。只有确认需要重跑同一精确模型版本时，才显式添加该开关。
