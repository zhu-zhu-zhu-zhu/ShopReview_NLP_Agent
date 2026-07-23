# ShopReview_NLP_Agent

电商用户评论情感分析 + 洞察 Agent 平台（生产实习结项选题）

## 说明书（先读）

请先阅读并按阶段执行：

**[电商评论情感分析Agent平台-完整实施框架说明书.md](./电商评论情感分析Agent平台-完整实施框架说明书.md)**

阶段 G（服务层 + 可视化大屏）展开说明：

**[docs/阶段G_服务层与大屏开发说明书.md](./docs/阶段G_服务层与大屏开发说明书.md)**

阶段 G 冒烟执行步骤（按勾选完成）：

**[docs/阶段G_冒烟测试执行步骤.md](./docs/阶段G_冒烟测试执行步骤.md)**

阶段 G 冒烟一键运行（端口 / 启动顺序 / 错误态）：

**[docs/阶段G_冒烟运行手册.md](./docs/阶段G_冒烟运行手册.md)**

API 字段契约（大屏 / Agent 共用）：

**[docs/api_contract_v0.md](./docs/api_contract_v0.md)**

阶段 H（Agent）展开说明：

**[docs/阶段H_Agent开发说明书.md](./docs/阶段H_Agent开发说明书.md)**

阶段 H 按勾选执行步骤（H0～H8，**大模型智能问答为主**）：

**[docs/阶段H_Agent开发执行步骤.md](./docs/阶段H_Agent开发执行步骤.md)**

推荐产品层顺序：**F 安全导出 → G 大屏+API → H Agent**。

大屏冒烟（Vite + React）：先 `backend\start.bat`，再 `dashboard\start.bat`；或根目录 `start_smoke_demo.bat`。

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
- 真实预测回写与 production DWS 管道代码准备（尚未执行导入）；
- 阶段 G 冒烟：FastAPI（`backend/`）+ 可视化大屏（`dashboard/`），读 `exports/agent/smoke`（正式总验收可后置）。

### 尚未完成

- 实际 NLP 模型训练；
- 真实模型预测文件交付；
- production 预测导入；
- 真实方面提取；
- production DWS 执行；
- 阶段 G 正式总验收（原步骤 7，建议结项前与总验一并做）；
- Agent 开发与最终集成（阶段 H，按 `docs/阶段H_Agent开发执行步骤.md`）。
