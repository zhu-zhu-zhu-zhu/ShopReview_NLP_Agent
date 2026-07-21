# Data Warehouse Framework Alignment

> 本文档是对原始《电商评论情感分析Agent平台-完整实施框架说明书》的实现补充，不替代或修改原说明书。  
> 文档状态：Draft v0.1，待只读数据检查与团队评审。

## 1. Project Context

| 项目 | 已确认内容 |
|---|---|
| 官方选题 | 基于公开数据集的电商用户评论情感分析 |
| 数据集 | Amazon Reviews 2023 — Amazon_Fashion |
| 评论源文件 | `Amazon_Fashion.jsonl` |
| 元数据源文件 | `meta_Amazon_Fashion.jsonl` |
| 文件格式 | JSON Lines / JSONL |
| 关联关系 | `review.parent_asin = metadata.parent_asin` |
| 分配分支 | `data-dev` |
| 分配角色 | 数仓开发 / Data Warehouse Development |

两份完整原始文件保存在共享仓库之外的本地路径中。它们不得复制到共享仓库，也不得提交到 Git。

## 2. Existing Framework Summary

原框架的目标是形成一条可答辩、可验证的评论分析闭环：公开评论数据进入 HDFS 和 Hive 分层数仓，经过 NLP 情感与方面分析形成 DWS 指标，再由 API、可视化大屏和受限工具型 Agent 使用。框架强调“先框架、后动手”，规划不代表功能已经完成。

总体技术链路原定为：

`CSV → HDFS → Hive ODS → Hive DWD → NLP 情感/方面分析 → Hive DWS → 可选 MySQL/JSON → FastAPI/大屏 → Agent`

项目范围包括抽样数据入仓、情感三分类、基线与主模型对比、轻量方面分析、指标服务、大屏、受限问数 Agent、周报与答辩材料；默认不做全网全量训练、从零预训练大模型、实时 Flink/Kafka、完整多模态、复杂多租户平台、任意 SQL Agent 或商业化运维。

框架先设置阶段 0（目标、数据、标签、分工和日历拍板），再安排 A 至 I 九个执行阶段：

1. A：环境与工程目录就绪；
2. B：数据集获取、数据字典、可复现抽样及训练集划分；
3. C：ODS 贴源数据进入 HDFS/Hive，并完成源端与 ODS 对账；
4. D：DWD 完成文本、时间、标签、有效性和去重等清洗；
5. E：NLP 基线与主模型训练、评估、误差分析及预测回写；
6. F：方面情感、主题指标和 DWS 聚合；
7. G：FastAPI 服务与可视化大屏；
8. H：通过白名单工具问数、解释和生成周报的评论洞察 Agent；
9. I：数据、模型、产品、Agent、报告与答辩的最终验收。

原框架中的数仓职责包括 HDFS 落地、ODS 追溯、DWD 清洗、DWS 聚合、分区与断点策略、行数对账、质量报告和服务数据准备。NLP 职责包括弱标签、基线/主模型、评估、误差分析、预测回写和方面情感。API 与大屏负责把 DWS 结果作为可验证产品展示；Agent 只能调用白名单工具获取数据，并应给出数据来源与时间窗。

预期交付物包括数据名片、数据字典、阶段检查单、HDFS 文件、Hive 分层表、验证 SQL、模型与评估报告、DWS 指标、API、大屏、Agent 工具日志、周报、结项报告和答辩材料。验收重点是源端与 ODS/DWD 行数可解释、标签与指标合法、模型对比可复现、预测可对账、大屏数字与服务端一致、Agent 固定剧本稳定且不编造数字。

原框架对数据字段采用通用假设，如 `review_id`、`product_id`、`user_id`、`rating`、`review_text`、`review_time`、`category` 和 `title`。这些假设尚未在本地 Amazon Fashion 文件上验证，不能当作已确认事实。

## 3. Confirmed Project Decisions

- 主数据集为 Amazon Reviews 2023 的 `Amazon_Fashion` 类别。
- 评论文本为英文。
- 源格式为 JSONL，不是 CSV。
- 评论与商品元数据分别位于两个源文件中。
- 两个数据源使用 `parent_asin` 关联。
- `asin` 表示具体商品标识；跨评论与商品元数据的主要关联使用 `parent_asin`。
- 完整原始数据保存在共享仓库外，并由 Git 忽略规则保护。
- 数仓工作只在 `data-dev` 分支进行。
- 团队分支为 `main`、`data-dev`、`agent-dev`、`nlp-model-dev` 和 `web-front-dev`；当前以 `main` 作为集成分支。
- 预期评论字段和元数据字段均处于“Expected — pending read-only dataset inspection”状态，不视为已验证字段。

## 4. Required Framework Adjustments

| Original assumption | Actual decision | Required adjustment |
|---|---|---|
| CSV 作为主要输入 | 两份 JSONL 源文件 | 设计流式、逐行、内存安全的 JSONL 检查与转换流程；不得整文件载入内存 |
| 一个评论源文件 | 评论文件与元数据文件分离 | 分别检查、抽样、落地、对账并记录各自来源 |
| 通用 `product_id` | `asin` 与 `parent_asin` | 明确字段语义；使用 `parent_asin` 进行评论与元数据关联 |
| 单表 `ods_review` | 评论 ODS 与元数据 ODS 分离 | 规划 `ods_amazon_fashion_review` 与 `ods_amazon_fashion_meta` |
| 通用质量/物流/服务方面 | 服装品类投诉方面 | 首版方面候选包括 size、color、material、comfort、workmanship、description mismatch、packaging、delivery、price |
| 原始数据位于仓库 `data/raw/` | 原始文件位于共享仓库之外 | 通过被忽略的 `.env` 或本地配置提供路径；仓库仅保存无秘密模板 |
| 通用 feature/develop 分支模型 | 团队已有固定分支 | 数仓仅用 `data-dev`；Agent/NLP/前端分别使用其已分配分支；集成是否长期直接进入 `main` 待团队确认 |
| Agent 可从通用数据源取数 | Agent 使用经过验证的数仓输出 | 通过受限 DWS/API/JSON 合同提供指标，禁止 Agent 从原始 JSONL 重算指标或执行不受限 SQL |

## 5. Data Warehouse Responsibility Boundary

### My responsibilities

- 对两份源文件进行只读、内存安全的结构检查；
- 生成可复现的 100 行和 10,000 行样本；
- 完成源数据质量画像与字段确认；
- 规划并执行 HDFS landing；
- 建设 Hive ODS、DWD 和 DWS；
- 编写验证 SQL、行数对账和质量检查；
- 向 Agent 与前端输出经过验证的数据；
- 维护数仓设计、字段、口径、接口和验收文档。

### Not my primary responsibilities

- NLP 模型训练与模型选型；
- Agent 提示词设计；
- Qwen 或其他 LLM API 集成；
- FastAPI Agent 编排；
- React 前端实现；
- 最终 PPT 视觉设计。

跨角色交付必须通过明确的数据合同完成，不能通过直接修改其他成员模块替代协作。

## 6. Planned Warehouse Layers

Hive 数据库暂定为 `review_dw`。下列表名和所有字段结构均为草案，必须经过只读数据检查和团队评审后才能实施。

### Draft ODS

- `ods_amazon_fashion_review`
- `ods_amazon_fashion_meta`

ODS 应尽量保留源字段和加载批次信息，分别对两类源文件进行追溯和对账。

### Draft DWD

- `dwd_amazon_fashion_review`
- `dwd_review_sentiment`
- `dwd_review_aspect`

DWD 计划负责字段标准化、时间解析、空文本处理、去重标记、评分弱标签、`parent_asin` 关联、模型预测结果和方面证据。实际字段必须先通过数据检查确认。

### Draft DWS

- `dws_sentiment_overview`
- `dws_sentiment_daily`
- `dws_sentiment_monthly`
- `dws_product_sentiment`
- `dws_store_sentiment`
- `dws_verified_purchase_sentiment`
- `dws_user_review_behavior`
- `dws_aspect_daily`
- `dws_negative_reason`
- `dws_alert_snapshot`

DWS 必须定义粒度、时间窗、分母、最低样本阈值、刷新方式与对账规则。任何排名或告警都不能在样本量不足时伪装为稳定结论。

## 7. Warehouse–Agent Interface

Warehouse provides:

- 经过验证的 DWS 指标；
- 商品情感汇总；
- 方面统计；
- 差评原因结果；
- 带来源与限制说明的代表性评论样本；
- 告警快照；
- 字段含义、粒度、时间窗和质量状态。

Agent provides:

- 受控工具调用；
- 基于证据的解释；
- 自然语言问答；
- 运营建议；
- 周报生成。

The Agent must not invent statistics and must not query unrestricted SQL. Agent 不得直接解析原始 JSONL 或自行重算数仓指标；工具没有返回的数据必须明确说明未知。

## 8. First Warehouse Milestones

1. **Milestone 1:** 对两份 JSONL 文件进行只读、流式结构检查。
2. **Milestone 2:** 生成可复现的 100 行与 10,000 行样本，并记录规则和随机种子。
3. **Milestone 3:** 创建数据名片和经过验证的数据字典。
4. **Milestone 4:** 确定 HDFS landing 格式、路径和对账方式。
5. **Milestone 5:** 创建并验证两张 ODS 表。
6. **Milestone 6:** 创建 DWD 清洗与评论—元数据关联明细。
7. **Milestone 7:** 集成 NLP 预测结果并验证行数与模型版本。
8. **Milestone 8:** 建设 DWS 表和 Agent/前端导出接口。

每个里程碑都应保留命令、关键输出、行数对账、异常说明和截图，不得用计划代替执行证据。

## 9. Open Decisions Requiring Team Confirmation

- 数仓使用完整数据集还是限定抽样范围；
- 开发样本、主实验样本和最终演示样本的规模；
- Hive 数据库名是否确认为 `review_dw`；
- JSONL 直接入仓，还是先流式转换为 Parquet/CSV；
- DWS 服务方式选择 JSON、MySQL 还是受限 API；
- 服装方面分类体系及中英文标准名称；
- 差评商品排名的最低评论量阈值；
- Agent 的离线降级方案；
- `main` 是否长期作为直接集成分支，以及是否需要单独的集成分支；
- 评分弱标签规则、NLP 输出合同和模型版本字段。

## 10. Current Status

- 原始实施框架已完整审阅；
- 已根据 Amazon Fashion 的确认决策形成对齐补充；
- 未执行 HDFS、Hive 或任何数据处理；
- 未验证源文件内部字段或统计数据；
- 下一步是对两份 JSONL 进行只读、内存安全的数据检查；
- 任何建表实施前均需要团队确认开放决策与草案结构。
