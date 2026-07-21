# 电商用户评论情感分析 + Agent 平台 — 完整实施框架说明书

> 项目目录：`ShopReview_NLP_Agent`  
> 选题：大数据方向 · 用户行为分析 · **3 · 基于公开数据集的电商用户评论情感分析**  
> 核心技术栈：HDFS, Hive, Python, NLP, 情感分类 + **LLM Agent**  
> 角色定位：数据分析师 / 数仓研发 / NLP / 后端 / 前端 / Agent  
> 原则：**先框架、后动手**；本文档为规划说明书，不等同于已执行。  
> 配套环境复用：`DAY6/tier4_stu`（HDFS + Hive）、既有大屏壳（DataCanvasLab / EcommerceDW-Dashboard）

---

## 0. 一句话目标

把公开电商评论数据集建成：

**CSV → HDFS → Hive ODS → Hive DWD（清洗）→ NLP 情感/方面分析 → Hive DWS →（可选 MySQL）→ 可视化大屏 + 评论洞察 Agent**

交付一条可答辩演示的闭环：入仓可验收、模型可对比、大屏可展示、Agent 可问数/出报告。

---

## 1. 项目边界（先定清楚）

| 做 | 不做（本周期默认不做，避免爆范围） |
|----|--------------------------------------|
| 公开评论数据集抽样入 HDFS/Hive 三层 | 全网上亿评论全量训练 |
| 情感三分类（正/中/负）+ 评估指标 | 从零预训练大模型 |
| 基线模型 + 主模型对比 | 实时 Flink/Kafka 流式情感（可列为展望） |
| 方面情感（物流/质量/服务/价格等）轻量实现 | 完整多模态（图文评论） |
| FastAPI 指标服务 + 情感大屏 | 复杂权限/多租户中台 |
| 评论洞察 Agent（问数 / 洞察 / 周报） | 任意 SQL 执行的“万能 Agent” |
| 结项报告 + 10～15 分钟答辩演示 | 商业化上线运维 |

**本机对应环境：**

| 角色 | 实际组件 |
|------|----------|
| HDFS + Hive | `tier4_stu`（DAY6） |
| 可选指标库 | `mysql_dw`（宿主机 `3307`）或本机 SQLite（演示够用） |
| 原始数据 | `ShopReview_NLP_Agent/data/raw/` |
| 工程根目录 | `ShopReview_NLP_Agent/` |
| 大屏前端 | 新建 `dashboard/` 或复用 DataCanvasLab 壳 |
| Agent | `agent/` + LLM API（通义 / DeepSeek 等） |

---

## 2. 总览：九个阶段

```
阶段0  立项拍板（目标、数据、分工、日历）
   ↓
阶段A  环境与目录就绪
   ↓
阶段B  数据集获取与抽样规范
   ↓
阶段C  ODS 贴源入库（CSV → HDFS → Hive）
   ↓
阶段D  DWD 清洗明细（可分析评论）
   ↓
阶段E  NLP 情感分类（基线 + 主模型 + 回写）
   ↓
阶段F  方面情感与主题指标（DWS）
   ↓
阶段G  服务层 + 可视化大屏
   ↓
阶段H  评论洞察 Agent
   ↓
阶段I  验收、结项报告与答辩材料
```

每一阶段都有：**目的 → 步骤清单 → 产出 → 验收标准 → 风险点**。

---

## 3. 阶段 0：立项拍板（开工前必须对齐）

### 目的

避免做到一半才发现「数据集太大 / 中英文分歧 / Agent 没人做」。

### 步骤清单

1. **确认商业目标（写进答辩第一页）**  
   示例表述（可微调）：  
   - 目标 1：对评论文本给出稳定的正/中/负情感标签，主模型 Macro-F1 **高于基线 ≥ 3～5 个百分点**。  
   - 目标 2：识别差评主要方面（质量/物流/服务/价格等），支撑品类运营。  
   - 目标 3：提供 Agent，可用自然语言查询「上周负面率 / Top 差评商品 / 方面趋势」，并一键生成周报摘要。

2. **拍板数据集语言与来源（三选一，只选一个主集）**

   | 方案 | 数据集 | 优点 | 缺点 |
   |------|--------|------|------|
   | A（推荐英文） | Amazon Reviews（Kaggle，按品类抽样） | PDF 附录点名；字段成熟；教程多 | 答辩需说明“公开英文电商评论” |
   | B（推荐中文） | 公开京东/淘宝评论集（DataFountain/Kaggle 中文评论） | 更贴国内电商叙事 | 清洗与分词更重 |
   | C | 多源小样本拼接 | 灵活 | 口径不统一，不推荐作主答辩数据 |

3. **拍板抽样规模（实习周期务实）**  
   - 开发冒烟：1～5 万条  
   - 主实验：**30～100 万条**（按品类/时间窗抽样）  
   - 不追求全量；报告写清抽样规则即可

4. **拍板标签定义**  
   - 方案 1（推荐）：`rating≥4 → 正；rating=3 → 中；rating≤2 → 负`（弱监督，需在报告说明局限）  
   - 方案 2：若数据集自带 sentiment 字段则优先用官方标签  
   - 人工金标：从测试集抽 **100～200 条** 人工复核，用于定性展示（非全量重标）

5. **拍板 Agent 范围（防爆炸）**  
   - 必做：问数（3～5 个固定剧本）+ 生成周报 Markdown  
   - 选做：差评突发告警文案、方面对比解读  
   - 禁止：让 Agent 直接改仓内数据、执行任意 DDL

6. **确认小组分工与里程碑日期**（写入 `docs/team_plan.md`）

### 阶段产出

- `docs/00_project_charter.md`（目标、数据、标签、分工、日历）  
- 已选定的数据集下载链接与许可证说明

### 验收标准

- 全组口头对齐：主数据集、语言、抽样上限、谁做 Agent  
- 商业目标可在 30 秒内讲清

---

## 4. 阶段 A：环境与目录就绪

### 目的

保证后面每一步有「能跑的平台」和统一工程骨架。

### 步骤清单

1. **确认 `tier4_stu` 健康**  
   - NameNode / DataNode / YARN / Hive Metastore / HiveServer2 为 healthy  
   - 宿主机可访问：`9870`（HDFS UI）、`10000`（HiveServer2）

2. **（可选）确认 `mysql_dw`**  
   - 若大屏要走 MySQL：端口 `3307`，库可新建 `review_sentiment`  
   - 若时间紧：DWS 结果用 JSON/SQLite 也可撑起演示

3. **创建项目目录骨架**

```text
ShopReview_NLP_Agent/
├── README.md
├── docs/                      # 说明书、验收记录、答辩材料
│   ├── 00_project_charter.md
│   ├── phase_*.md             # 各阶段验收清单
│   └── architecture.md
├── data/
│   ├── raw/                   # 原始 CSV（勿提交超大文件到 git）
│   ├── sample/                # 小样本
│   ├── processed/             # 本地清洗中间结果
│   └── state/                 # 断点、抽样清单
├── sql/
│   ├── 01_ods_review.sql
│   ├── 02_dwd_review.sql
│   ├── 03_dws_tables.sql
│   └── 04_qa_*.sql
├── scripts/
│   ├── download_dataset.py
│   ├── sample_dataset.py
│   ├── load_ods_to_hdfs.py
│   ├── run_dwd_clean.py
│   ├── train_baseline.py
│   ├── train_transformer.py
│   ├── predict_and_writeback.py
│   ├── build_dws.py
│   ├── sync_to_mysql.py       # 可选
│   └── qa_*.py
├── models/
│   ├── baseline/
│   └── transformer/
├── nlp/
│   ├── preprocess.py
│   ├── label_mapping.py
│   ├── aspects.py             # 方面词典/规则
│   └── metrics.py
├── backend/
│   ├── app/main.py            # FastAPI
│   ├── app/services/
│   └── requirements.txt
├── agent/
│   ├── tools/                 # 查询、报告工具
│   ├── prompts/
│   ├── orchestrator.py
│   └── demo_scripts.md        # 答辩固定问法
├── dashboard/                 # 大屏前端（或文档说明复用路径）
└── reports/                   # 自动生成的周报、评估表
```

4. **安装本机 Python 依赖（建议独立 venv）**  
   - 基础：`pandas, pyarrow, scikit-learn, jieba(中文), nltk/spacy(英文可选)`  
   - 深度学习：`torch, transformers, datasets, accelerate`（按机器显存选模型）  
   - 服务：`fastapi, uvicorn, pymysql(可选)`  
   - Agent：`openai` 兼容 SDK 或厂商 SDK

5. **连通性冒烟**  
   - Beeline：`SHOW DATABASES;`  
   - `hdfs dfs -ls /`  
   - 本机 Python 能 `import` 关键包

6. **（可选）停非必要服务**  
   - 数仓 + 训练阶段优先保 tier4；HBase/tier5 不必开

### 阶段产出

- 可登录 Beeline / HDFS  
- 完整目录骨架  
- `docs/phase_A_checklist.md`

### 验收标准

- HiveServer2、NameNode 可用  
- 目录结构按上文存在  
- `python -c "import pandas, sklearn"` 成功

### 风险点

- Windows + Docker 内存不足：训练时关闭无关容器  
- 大 CSV 不要塞进 git；用 `.gitignore` 忽略 `data/raw/*.csv`

---

## 5. 阶段 B：数据集获取与抽样规范

### 目的

拿到「可复现、可讲解」的主数据，而不是不可描述的随意文件。

### 步骤清单

1. **下载原始数据到 `data/raw/`**  
   - 记录来源 URL、版本、下载日期 → 写入 `docs/data_card.md`

2. **编写数据字典 `docs/data_dictionary.md`**（按实际字段改）

   | 字段 | 类型 | 含义 | 备注 |
   |------|------|------|------|
   | review_id | string | 评论唯一 ID | 主键 |
   | product_id | string | 商品 ID | |
   | user_id | string | 用户 ID | 可脱敏 |
   | rating | int/float | 星级 1～5 | 用于弱标签 |
   | review_text | string | 评论文本 | 主输入 |
   | review_time | string/datetime | 评论时间 | 解析为 dt |
   | category | string | 品类 | 分析维度 |
   | title | string | 标题（若有） | 可拼入文本 |

3. **编写抽样脚本 `scripts/sample_dataset.py`**  
   - 支持参数：`--n 100000`、`--categories ...`、`--seed 42`  
   - 输出：`data/sample/reviews_sample.csv` + `data/state/sample_manifest.json`（含随机种子、过滤条件、行数）

4. **质量快检（抽样后立刻做）**  
   - 总行数、空 `review_text` 比例、星级分布、品类分布、时间范围  
   - 输出表：`docs/phase_B_profile.md`

5. **划分训练/验证/测试（按 review_id 或时间）**  
   - 推荐：时间切分（更贴近业务）或分层抽样（按情感标签比例）  
   - 比例示例：训练 70% / 验证 15% / 测试 15%  
   - 落盘：`data/processed/train.csv|valid.csv|test.csv`  
   - **禁止**用测试集调参

### 阶段产出

- 原始与抽样数据  
- 数据字典、数据名片、抽样清单  
- 训练/验证/测试划分文件

### 验收标准

| 检查项 | 期望 |
|--------|------|
| 抽样可复现 | 同 seed 得到同行数/同分布 |
| 空文本率 | 报告中给出；后续 DWD 会过滤 |
| 划分无泄漏 | 同一 review_id 不跨集合 |
| 文档齐全 | data_card / data_dictionary / profile |

### 风险点

- Kaggle 下载需账号/网络：提前下载并做本地备份  
- 字段名不一致：在 `nlp/preprocess.py` 做统一 rename

---

## 6. 阶段 C：ODS 贴源入库（CSV → HDFS → Hive）

### 目的

原始评论**原样进仓**，按日期分区落 HDFS，供后续清洗与追溯。

### 步骤清单

1. **建 Hive 库**（建议统一）  
   - `CREATE DATABASE IF NOT EXISTS review_dw;`  
   - 与 MySQL 库名可不同，文档写清映射

2. **建 ODS 外表 `ods_review`**（`sql/01_ods_review.sql`）  
   - 字段：与抽样 CSV 对齐的贴源字段  
   - 分区：`dt STRING`（按评论日期；若无时间则用加载批次 `batch_id`）  
   - 格式：TEXTFILE 或 CSV SerDe；分隔符与文件一致  
   - LOCATION：如 `/data/review_dw/ods/ods_review`

3. **编写加载脚本 `scripts/load_ods_to_hdfs.py`**  
   - 读本地 CSV → 按 `dt` 写入 `.../ods_review/dt=yyyy-MM-dd/part-*.csv`  
   - 支持小样本先跑、全量抽样再跑  
   - Windows → 容器：`hdfs dfs -put` 或挂载 `data-shared` 再 put

4. **修复分区**  
   - `MSCK REPAIR TABLE ods_review;`  
   - 或按分区 `ALTER TABLE ... ADD PARTITION`

5. **ODS 质量检查**  
   - `COUNT(*)` 与本地抽样行数一致（允许说明尾差）  
   - 抽 3 个分区 `SELECT * ... LIMIT 20`  
   - 星级分布直方图 SQL

### 阶段产出

- HDFS 分区文件  
- Hive `review_dw.ods_review`  
- `docs/phase_C_checklist.md`

### 验收标准

| 检查项 | 期望 |
|--------|------|
| 行数 | ≈ 抽样 CSV 总行数 |
| 分区 | 存在多个 `dt=` 或明确 batch 分区 |
| 内容 | 未做情感推断、未删业务字段（贴源） |
| 可追溯 | 能从分区路径回到加载批次说明 |

### 风险点

- 小文件过多：可按天合并 part  
- 编码问题：统一 UTF-8；中文注意 Hive serde

---

## 7. 阶段 D：DWD 清洗明细（可分析评论）

### 目的

产出「可做 NLP 的明细」：去空评、规范化文本、解析时间、映射弱标签，格式建议 Parquet。

### 步骤清单

1. **建内部表 `dwd_review`**（`sql/02_dwd_review.sql`）  
   - 字段示例：  
     `review_id, product_id, user_id, category, rating, review_text, review_text_clean, review_time, sentiment_label, label_source, text_len, dt`  
   - 分区：`dt`  
   - 存储：PARQUET

2. **清洗规则（写入 `nlp/preprocess.py` + `scripts/run_dwd_clean.py`）**

   | 规则 | 处理 |
   |------|------|
   | `review_text` 空/仅空白 | 丢弃或进废件表 |
   | 过短（如 < 5 字符） | 丢弃或标记 `too_short` |
   | HTML/URL/表情噪声 | 适度清洗，保留语义 |
   | 全角/繁简（中文） | 可选统一 |
   | 英文 | lower + 基础标点规范 |
   | 时间 | 解析失败则 `dt='unknown'` 并计数 |
   | 情感弱标签 | 按阶段 0 约定从 rating 映射 |
   | 去重 | 同 `review_id` 保留一条；可选同用户同商品同文去重 |

3. **执行策略**  
   - 先 1 天/1 品类冒烟 → 再全量抽样  
   - 若 Hive 动态分区写 Parquet OOM：改 **按天/按周** 批跑（复用 DAY9 经验）  
   - 断点文件：`data/state/dwd_done_dates.txt`

4. **废件与质量报表**  
   - 统计：丢弃原因占比、标签分布、文本长度分位数  
   - SQL：`sql/04_qa_dwd.sql`

5. **导出训练视图（可选）**  
   - 从 DWD 再导出 `train/valid/test`（与阶段 B 划分一致）供本机训练，避免训练时打爆 Hive

### 阶段产出

- Hive `dwd_review`  
- 清洗规则文档 + QA 报告  
- `docs/phase_D_checklist.md`

### 验收标准

- 空文本率 ≈ 0（在 DWD 内）  
- `sentiment_label` 仅含约定类别  
- 行数明显 ≤ ODS（因过滤），差值可解释  
- 抽样 20 条人工看：清洗未把句子洗没语义

### 风险点

- 过度清洗导致模型输入失真  
- 弱标签与真实情感不一致（反讽、3 星好评等）——必须在报告「局限」中写明

---

## 8. 阶段 E：NLP 情感分类（核心算法阶段）

### 目的

完成可对比、可回写、可答辩的情感分类能力。

### 步骤清单

#### E1. 基线模型（必须先做）

1. 特征：TF-IDF（中文先 `jieba` 分词；英文直接 token）  
2. 分类器：LogisticRegression 或 LinearSVM  
3. 脚本：`scripts/train_baseline.py`  
4. 产出：`models/baseline/` + `reports/baseline_metrics.json`  
5. 输出指标：Accuracy、Precision/Recall/F1（macro/weighted）、混淆矩阵图

#### E2. 主模型（Transformer 微调）

1. 模型选择（按语言与机器）  

   | 条件 | 推荐 |
   |------|------|
   | 中文 + 有 GPU | `hfl/chinese-roberta-wwm-ext` 或 `bert-base-chinese` |
   | 英文 + 有 GPU | `distilbert-base-uncased` / `roberta-base` |
   | 仅 CPU / 时间紧 | 蒸馏小模型或减少 max_len、epoch；或主讲基线+轻量模型 |

2. 训练配置建议（起点，按显存改）  
   - `max_length=128` 或 `256`  
   - `batch_size=16/32`  
   - `epochs=2～3`  
   - 早停：按验证集 Macro-F1  

3. 脚本：`scripts/train_transformer.py`  
4. 产出：`models/transformer/` + `reports/transformer_metrics.json` + 训练曲线

#### E3. 模型对比与误差分析（答辩加分）

1. 同测试集对比表：基线 vs 主模型  
2. 错误样例 20 条：假阴性差评、反讽、中性难例  
3. 星级与预测不一致案例专题（刷评/文不对题线索）  
4. 写入 `docs/model_evaluation.md`

#### E4. 全量（抽样集）预测回写

1. 脚本：`scripts/predict_and_writeback.py`  
2. 对 `dwd_review` 全部分区预测：`pred_label, pred_score, model_version, inferred_at`  
3. 落表策略二选一（文档固定一种）：  
   - **推荐**：新表 `dwd_review_sentiment`（review_id 关联）  
   - 或 `INSERT OVERWRITE` 宽表（字段变多时迁移成本高）  
4. Hive 验收：标签分布、按品类负面率、与弱标签一致性（cohen's kappa 可选）

### 阶段产出

- 基线与主模型产物  
- 评估报告与混淆矩阵  
- `dwd_review_sentiment`（或等价表）  
- `docs/phase_E_checklist.md`

### 验收标准

| 检查项 | 期望 |
|--------|------|
| 基线可复现 | 一键脚本跑出指标 |
| 主模型 | 测试集 Macro-F1 **≥ 基线**（目标高出 3～5pt，视数据而定） |
| 回写 | 行数与 DWD 可对齐（或说明未预测子集） |
| 可解释材料 | 混淆矩阵 + 错误样例 |

### 风险点

- GPU/内存不够：减小模型与序列长；或主答辩用基线+小模型，Transformer 作拓展说明  
- 类别不平衡：用 class_weight / 过采样 / 以 F1 为选模标准  
- 数据泄漏：严禁把测试评论的文本统计拟合进训练向量器时误用全量

---

## 9. 阶段 F：方面情感与主题指标（DWS）

### 目的

从「整句情感」升级到「为什么差 / 哪方面差」，并形成可服务化的汇总表。

### 步骤清单

1. **方面体系定义（先小后大）**  
   建议固定 5～6 个方面（写入 `nlp/aspects.py`）：  
   - 质量 / 物流 / 服务 / 价格 / 包装 / 其他  
   - 每方面：关键词词典（中英文各一套）+ 简单规则（出现词则命中）  
   - 进阶（选做）：方面级分类模型或提示词抽取（注意成本与稳定性）

2. **方面情感规则（务实版）**  
   - 命中方面词的句子/子句，继承整句 `pred_label`，或对子句再跑一次轻量情感  
   - 产出明细：`dwd_review_aspect(review_id, aspect, aspect_sentiment, evidence_span)`

3. **建 DWS 表（`sql/03_dws_tables.sql`）**

   | 表名 | 粒度 | 核心指标 |
   |------|------|----------|
   | `dws_sentiment_daily` | dt + category | 评论量、正/中/负占比、负面率、均分 |
   | `dws_product_sentiment` | product_id + 近 N 日 | 负面率、评论量、均分 |
   | `dws_aspect_daily` | dt + aspect + category | 方面命中量、方面负面率 |
   | `dws_inconsistency_daily` | dt | 高星负文 / 低星正文 数量与占比 |
   | `dws_alert_snapshot` | 快照 | 负面率环比暴涨的品类/商品 |

4. **脚本 `scripts/build_dws.py`**  
   - 优先 Hive SQL 聚合；复杂规则可 Python 算完再 load  
   - 支持按日增量；断点 `data/state/dws_done_dates.txt`

5. **业务抽查（分析师视角）**  
   - 大促/已知事件日负面率是否异常  
   - Top10 差评商品是否「评论量足够」（避免 n=2 就上榜）  
   - 方面分布是否合理（不是 90%「其他」）

### 阶段产出

- 方面词典与规则说明  
- Hive DWS 系列表  
- `docs/phase_F_checklist.md` + 若干分析结论草稿

### 验收标准

- 每日情感表有数；负面率在 0～1  
- Top 差评榜有最低评论量阈值（如 ≥20）  
- 方面表不是空的；「其他」占比有记录  
- 与 DWD 抽样合计一致（同 dt 评论量）

### 风险点

- 词典方面覆盖不足 → 迭代词典，不要一上来上复杂 ABSA  
- 排行无阈值 → 业务解读会被问倒

---

## 10. 阶段 G：服务层 + 可视化大屏

### 目的

把 DWS 变成「可演示产品」，而不是一堆表。

### 步骤清单

1. **（可选）同步 MySQL**  
   - 库：`review_sentiment`  
   - 表与 DWS 对齐；Upsert 或按日覆盖  
   - 脚本：`scripts/sync_to_mysql.py`

2. **FastAPI 后端 `backend/app/main.py`**  
   建议接口（与大屏/Agent 共用）：  

   | 接口 | 作用 |
   |------|------|
   | `GET /api/health` | 健康检查 |
   | `GET /api/kpi` | 总评论、负面率、不一致率等 |
   | `GET /api/trend` | 情感日趋势 |
   | `GET /api/top-negative-products` | 差评商品 TOP |
   | `GET /api/aspects` | 方面分布/趋势 |
   | `GET /api/alerts` | 告警列表 |
   | `GET /api/samples` | 差评样例文本（脱敏） |

3. **大屏面板设计（一屏讲完故事）**

   | 区域 | 内容 |
   |------|------|
   | 顶栏 | 项目名「评论情感洞察」+ 数据时间窗 |
   | KPI | 评论量 / 负面率 / 高星负文率 / Top 差评品类 |
   | 中央 | 情感趋势（正中负堆积或负面率折线） |
   | 左 | 方面负面占比（饼/条） |
   | 右 | 差评商品 TOP10 + 告警 |
   | 底 | 样例差评滚动 / 数据源说明 |

4. **前端实现**  
   - 优先复用已有大屏壳，改 API 与文案  
   - 开发模式关闭 Mock，直连后端  
   - 准备一键启动脚本：`dashboard/start.bat`、`backend/start.bat`

5. **截图与录屏**  
   - 全屏大屏图进结项报告  
   - 30～60 秒操作录屏备用

### 阶段产出

- 可访问的 API + 大屏  
- `docs/phase_G_checklist.md`  
- 大屏截图素材

### 验收标准

- `/api/health` 正常；KPI 与 Hive/MySQL 抽样一致  
- 大屏四类核心面板有真实数据  
- 断网或后端挂掉时有明确错误提示（不要静默 Mock 瞒过答辩）

### 风险点

- 跨域与端口：统一 `5173/8080` 一类约定  
- 大屏数据写死：验收时当场改日期参数验证

---

## 11. 阶段 H：评论洞察 Agent（差异化）

### 目的

实现「预测/分析 → 解读 → 行动建议」闭环，对齐选题介绍中的 Agent 思路，但工具白名单可控。

### 步骤清单

1. **定义 Agent 角色与系统提示**（`agent/prompts/system.md`）  
   - 你是电商评论分析助手；只能通过工具取数；回答必须给出数据出处与时间窗；不确定就说不确定。

2. **注册工具（Function Calling）——只做这些**

   | 工具名 | 功能 | 实现 |
   |--------|------|------|
   | `get_kpi` | 总览指标 | 调后端 `/api/kpi` |
   | `get_sentiment_trend` | 趋势 | `/api/trend` |
   | `get_top_negative_products` | 差评榜 | `/api/top-negative-products` |
   | `get_aspect_stats` | 方面统计 | `/api/aspects` |
   | `get_alerts` | 告警 | `/api/alerts` |
   | `search_review_samples` | 样例评论 | `/api/samples` |
   | `generate_weekly_report` | 生成周报 md | 聚合上述工具结果填模板 |

3. **编排实现 `agent/orchestrator.py`**  
   - 推荐：ReAct / OpenAI tools 循环（最多 N 步）  
   - 记录每次 tool call 日志，便于答辩展示「Agent 确实在调工具」  
   - 配置：API Key 放环境变量，禁止写进仓库

4. **答辩固定剧本（必须写进 `agent/demo_scripts.md`）**

   1. 「最近 7 天整体负面率是多少？和前 7 天比呢？」  
   2. 「负面率最高的 5 个商品是什么？主要差在哪些方面？」  
   3. 「有没有高星级但文本很负的异常评论？举 3 个例子。」  
   4. 「请生成本周评论情感分析周报。」  
   5. （选）「物流方面差评是否在上升？」

5. **前端入口**  
   - 大屏侧边「智能问答」抽屉，或独立 `/agent` 页  
   - 展示：思考步骤 / 调用了哪些工具 / 最终答案

6. **安全与稳定性**  
   - 工具参数校验（日期格式、limit 上限）  
   - 超时与重试；LLM 失败时仍可展示工具原始 JSON  
   - 提示词注入防护：用户输入不当作 SQL

### 阶段产出

- 可演示 Agent  
- 工具日志样例  
- 自动周报 `reports/weekly_*.md`  
- `docs/phase_H_checklist.md`

### 验收标准

- 5 个剧本中至少 **4 个稳定可跑**  
- 答案中能看到具体数字，且与 API/大屏一致  
- 周报文件成功生成  
- 日志能证明发生了 tool call（不是纯编造）

### 风险点

- 无 Key / 网络不通：准备「离线演示模式」（预设 tool 结果 + 模板回答）作为 Plan B  
- Agent 幻觉：强制「必须先调工具再回答」

---

## 12. 阶段 I：验收、结项报告与答辩

### 目的

对齐评分表把材料补齐，保证 10～15 分钟讲完。

### 硬验收清单

| 类别 | 检查项 | 验证方式 |
|------|--------|----------|
| 数据 | ODS 行数 ≈ 抽样源 | Hive COUNT |
| 数据 | DWD 可分析、标签合法 | QA SQL |
| 模型 | 基线 + 主模型指标表 | reports/*.json |
| 模型 | 预测已回写 | 表抽样 |
| 主题 | DWS 指标可查 | 趋势/TOP/方面 |
| 产品 | 大屏真实数据 | 现场刷新 |
| Agent | 固定剧本可演示 | 现场问答 |
| 文档 | 架构、分工、局限 | 结项报告 |

### 结项报告建议目录

1. 项目背景与目标  
2. 数据来源与抽样说明  
3. 总体架构（数仓 + NLP + 服务 + Agent）  
4. 数据处理（ODS/DWD/DWS）  
5. 算法与实验（对比、误差分析）  
6. 产品展示（大屏截图）  
7. Agent 设计与演示  
8. 团队分工与进度  
9. 结论、创新点、不足与展望  

### 答辩演示脚本（约 12 分钟）

| 时间 | 内容 |
|------|------|
| 0～1 min | 选题与业务痛点 |
| 1～3 min | 架构图与数据流 |
| 3～5 min | Hive 分层 + 质量数字 |
| 5～8 min | 模型对比与错误样例 |
| 8～10 min | 大屏演示 |
| 10～12 min | Agent 问数 + 生成周报 |
| 12～13 min | 分工与展望 |

### 阶段产出

- `docs/结项报告.md`（再转 Word/PDF）  
- PPT / 演示备注  
- 全阶段 checklist 归档

---

## 13. 推荐日历（可按组员人数压缩）

| 天数 | 阶段 | 体感 |
|------|------|------|
| 第 1 天上午 | 0 立项 + A 环境 | 0.5 天 |
| 第 1 天下午 | B 数据 | 0.5 天 |
| 第 2 天 | C ODS + D DWD | 1 天 |
| 第 3～4 天 | E NLP | 1.5～2 天 |
| 第 5 天 | F DWS + 方面 | 1 天 |
| 第 6 天 | G 大屏 + API | 1 天 |
| 第 7 天 | H Agent | 1 天 |
| 第 8 天 | I 结项与彩排 | 1 天 |

**原则：每阶段 checklist 勾完再进下一阶段。**

---

## 14. 关键决策清单（写进 charter，勿悬空）

1. 数据集：Amazon 英文 / 中文电商评论？  
2. 抽样上限：多少万条？哪些品类？  
3. 标签：星级映射 or 自带标签？  
4. 主模型：哪个预训练模型？有无 GPU？  
5. DWS 服务：MySQL or JSON/SQLite？  
6. Agent：哪家 LLM API？有无离线 Plan B？  
7. 大屏：新建 or 复用哪个前端壳？  
8. 库名：Hive `review_dw` 是否确认？

---

## 15. 与课程既有成果的关系

| 已有能力 | 本项目如何复用 |
|----------|----------------|
| tier4 HDFS/Hive | 评论三层入仓 |
| DAY7 淘宝分析指标→API→大屏 | 换主题为情感指标 |
| DAY9 数仓按天/周批跑与断点 | DWD/DWS 防 OOM |
| DataCanvasLab / EcommerceDW-Dashboard | 大屏 UI 壳 |
| 实验报告体例 | 结项报告与截图规范 |

本项目不是重复淘宝 PV/UV，而是 **评论文本 NLP + 情感主题数仓 + Agent**，形成差异化答辩点。

---

## 16. 开工入口

- **同意本说明书**：回复「按框架开始」，并回复第 14 节决策（或「按推荐：Amazon 抽样 + 星级弱标签 + 复用大屏壳 + DeepSeek/通义 Agent」）。  
- **要改**：例如必须中文数据、不做方面、先不做 MySQL——说清楚后改 charter 再动手。

**文档状态**：实施框架已定稿；未默认等同于已执行建表/训练/部署。

---

## 附录 A：建议验收记录文件列表

```text
docs/phase_A_checklist.md
docs/phase_B_checklist.md
docs/phase_C_checklist.md
docs/phase_D_checklist.md
docs/phase_E_checklist.md
docs/phase_F_checklist.md
docs/phase_G_checklist.md
docs/phase_H_checklist.md
docs/phase_I_checklist.md
docs/data_card.md
docs/data_dictionary.md
docs/model_evaluation.md
docs/architecture.md
agent/demo_scripts.md
```

## 附录 B：选题与评分对齐（答辩自检）

| 评分项 | 权重 | 本项目证据 |
|--------|------|------------|
| 选题与创新 | 10% | 情感数仓 + 方面 + Agent 闭环 |
| 技术方案 | 50% | 分层入仓、双模型对比、回写、API、大屏、Agent 工具 |
| 团队协作 | 15% | charter 分工表 + 各成员交付物 |
| 项目展示 | 15% | 架构清晰、现场演示流畅 |
| 答辩表现 | 10% | 固定剧本 + 局限坦诚 + 展望真实 |

## 附录 C：参考数据源（来自选题介绍）

- Kaggle：https://www.kaggle.com/datasets  
- DataFountain：https://www.datafountain.cn/datasets  
- 说明：公开数据请遵守许可证；报告中注明来源与抽样方式。
