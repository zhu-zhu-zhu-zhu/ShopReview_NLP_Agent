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
- `tfidf_logreg_oof_v1` 真实 OOF 预测导入与 production Hive DWS；
- Hive DWS → MySQL 服务层同步实现与合成单元测试；
- production Hive DWS 的 MySQL ExportOnly 本地导出与校验；
- 独立 `shopreview_mysql` 服务实例、三张 serving 表与 Hive/MySQL 对账；
- Agent 专用只读 `agent_reader` 账户和本地安全连接交接；
- Production DWS v2 十张扩展指标表与 13 表 MySQL serving 层；
- `keyword_rules_v1` 方面汇总和差评原因汇总；
- Hive/MySQL v2 逐表对账与 `shopreview_serving_prod_v2.zip` 数据库交接包。

### 尚未完成

- Agent/FastAPI 新增十表路由；
- 前端组件集成；
- 演示与展示验证；
- 可选的未来学习型方面模型；
- Agent 最终集成。
