# ShopReview_NLP_Agent

电商用户评论情感分析 + 洞察 Agent 平台（生产实习结项选题）

## 说明书（先读）

请先阅读并按阶段执行：

**[电商评论情感分析Agent平台-完整实施框架说明书.md](./电商评论情感分析Agent平台-完整实施框架说明书.md)**

阶段 H（Agent）展开说明：

**[docs/阶段H_Agent开发说明书.md](./docs/阶段H_Agent开发说明书.md)**

## 选题对应

| 项 | 内容 |
|----|------|
| 方向 | 大数据 · 用户行为分析 |
| 编号 | 3 |
| 名称 | 基于公开数据集的电商用户评论情感分析 |
| 技术栈 | HDFS, Hive, Python, NLP, 情感分类 + LLM Agent |

## 状态

### 已完成

- 实施框架与 Amazon Fashion 决策对齐；
- Phase B 有界数据检查；
- Phase C 100 行 HDFS/Hive ODS smoke test；
- Phase D 协调匹配样本 JOIN 与 DWD smoke test；
- Phase E NLP 数据交接与预测写回契约 smoke test（合成接口记录，不是模型输出）；
- Phase F DWS 聚合与 Agent 安全 JSON 导出 smoke test（方面记录为合成契约数据）；
- production-v1 生产实验范围 HDFS 落盘（批次 `prod_v1_100k`）；
- production-v1 分区 ODS；
- production-v1 分区 Parquet DWD；
- production-v1 正式 NLP 输入导出与交付验证；
- 真实预测回写与 production DWS 管道代码准备（尚未执行导入）。

### 尚未完成

- 实际 NLP 模型训练；
- 真实模型预测文件交付；
- production 预测导入；
- 真实方面提取；
- production DWS 执行；
- Agent FastAPI 集成；
- Dashboard；
- Agent 最终集成。
