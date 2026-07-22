# ShopReview_NLP_Agent

电商用户评论情感分析 + 洞察 Agent 平台（生产实习结项选题）

## 说明书（先读）

请先阅读并按阶段执行：

**[电商评论情感分析Agent平台-完整实施框架说明书.md](./电商评论情感分析Agent平台-完整实施框架说明书.md)**

## 选题对应

| 项 | 内容 |
|----|------|
| 方向 | 大数据 · 用户行为分析 |
| 编号 | 3 |
| 名称 | 基于公开数据集的电商用户评论情感分析 |
| 技术栈 | HDFS, Hive, Python, NLP, 情感分类 + LLM Agent |

## NLP 状态

已完成：

- production-v1 NLP 输入校验；
- TF-IDF + Logistic Regression 基线模型；
- 独立留出测试集评估；
- 5 折 OOF 全量生产预测生成；
- 预测数据契约校验。

待完成：

- 数仓预测导入；
- production DWS 执行；
- Agent 集成；
- 可选的 Transformer 模型对比。
