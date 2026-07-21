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

## 状态

### 已完成

- 实施框架与 Amazon Fashion 决策对齐；
- Phase B 有界数据检查；
- Phase C 100 行 HDFS/Hive ODS smoke test；
- Phase D 协调匹配样本 JOIN 与 DWD smoke test；
- Phase E NLP 数据交接与预测写回契约 smoke test（合成接口记录，不是模型输出）。

### 尚未完成

- 完整数据 HDFS 加载；
- 完整数据生产 ODS；
- 完整数据生产 DWD；
- 实际 NLP 模型训练；
- 实际模型预测导入；
- DWS；
- API；
- Dashboard；
- Agent 集成。
