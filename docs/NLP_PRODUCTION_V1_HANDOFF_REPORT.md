# Amazon Fashion 正式 NLP 数据交付报告

## 一、交付范围

| 项目 | 实测结果 |
|---|---:|
| 来源 Hive 表 | `review_dw.dwd_amazon_fashion_review` |
| 批次 ID | `prod_v1_100k` |
| DWD 行数 | 99,703 |
| 符合 NLP 输入条件的行数 | 99,703 |
| 导出行数 | 99,703 |

`prod_v1_100k` 是本项目正式实验子集，不代表完整 Amazon Fashion 数据集。导出只读取该批次已清洗、去重并通过 DWD 质量门槛的记录，没有训练 NLP 模型，也没有生成或导入模型预测。

## 二、输出字段

| 字段 | 含义 | 是否必填 |
|---|---|---|
| `review_key` | 数仓生成的稳定评论标识，必须原样保留 | 是 |
| `review_text_clean` | 已清洗且非空的评论文本 | 是 |
| `rating_label` | 根据星级生成的弱监督标签 | 是 |
| `rating` | 原始星级评分 | 是 |
| `parent_asin` | 商品族标识 | 否 |
| `main_category` | 元数据匹配后的商品主类目 | 否 |
| `review_time` | 解析后的评论时间 | 否 |
| `load_batch_id` | 数据批次标识，本次固定为 `prod_v1_100k` | 是 |

导出 schema 严格限定为以上八个字段，不包含 `user_id`、原始元数据对象或其他隐私字段。

## 三、弱标签说明

- 1–2 星映射为 `negative`；
- 3 星映射为 `neutral`；
- 4–5 星映射为 `positive`。

`rating_label` 来自星级规则，是用于监督训练和评估准备的弱标签，不是 NLP 模型预测，也不能作为真实模型效果的证明。

## 四、数据质量验证

| 检查项 | 实测结果 | 结论 |
|---|---:|---|
| 导出唯一 `review_key` | 99,703 | PASS |
| 重复 `review_key` | 0 | PASS |
| null / 空白 `review_key` | 0 | PASS |
| 空白 `review_text_clean` | 0 | PASS |
| 非法 `rating_label` | 0 | PASS |
| `negative` | 15,640 | 对账通过 |
| `neutral` | 10,913 | 对账通过 |
| `positive` | 73,150 | 对账通过 |
| 评分范围 | 1.0–5.0 | PASS |
| 有 `parent_asin` | 99,703（100%） | PASS |
| 有 `main_category` | 99,703（100%） | PASS |
| 有 `review_time` | 99,703（100%） | PASS |
| Hive 导出表与 eligible DWD 差值 | 0 | PASS |

导出表、JSONL、摘要与 manifest 的行数均为 99,703。JSONL 使用 UTF-8、`ensure_ascii=False` 和固定字段顺序逐行写出；写入采用临时文件替换，失败时不会留下半成品。由于当前 Hive 2.3.2 对多分区 Parquet 的自动小文件合并存在读取器兼容问题，导出 SQL 仅在本会话使用标准 `HiveInputFormat` 并关闭自动合并，未修改生产 DWD 或全局 Hive 配置。

## 五、输出文件

| 文件 | 路径或结果 |
|---|---|
| 本地 NLP JSONL（Git 忽略） | `data/processed/nlp_production_v1/nlp_input_prod_v1.jsonl` |
| 安全摘要 | `reports/nlp_handoff/nlp_input_prod_v1_summary.json` |
| 交付 manifest | `reports/nlp_handoff/nlp_input_prod_v1_manifest.json` |
| 文件大小 | 46,005,546 bytes |
| SHA-256 | `e10925187eea5fc34721778c0a6e2ea5b8c7492a1325fd0c49966dafe3f12714` |

报告、摘要和 manifest 不包含完整评论文本、完整用户标识、凭据或 API 密钥。真实 JSONL 保持忽略和未跟踪状态。

## 六、NLP 成员返回格式

NLP 成员完成真实模型推理后，应返回：

- `review_key`
- `pred_label`
- `pred_score`
- `model_version`
- `inferred_at`

NLP 开发者不得重新生成、格式化或修改 `review_key`。数仓将使用原始键进行存在性、唯一性和写回对账。

## 七、责任边界

数仓成员负责：

- 准备清洗后的 NLP 输入；
- 验证键、字段、标签和批次；
- 导出数据并生成可审计摘要；
- 后续导入并对账真实预测。

NLP 成员负责：

- 训练 baseline 与主模型；
- 评估并记录模型指标；
- 返回预测结果和 `model_version`；
- 完整保留数仓提供的 `review_key`。

## 八、局限性

- 本次仅覆盖 production-v1 实验子集，不是完整 Amazon Fashion 数据集；
- 弱标签来自星级评分，不等同于人工真值；
- 尚未导入任何真实模型预测；
- 尚未建设 production DWS。

## 九、验收结论

正式 DWD、eligible 输入、Hive 导出表和本地 JSONL 均为 99,703 行；键唯一性、必填字段、标签域、批次、schema 和 SHA-256 对账全部通过。

NLP PRODUCTION EXPORT RESULT: PASS

NLP HANDOFF VALIDATION RESULT: PASS
