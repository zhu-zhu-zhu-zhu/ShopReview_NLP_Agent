# ShopReview_NLP_Agent

基于 Amazon Fashion 公开评论数据的端到端情感分析平台。项目覆盖流式数据检查、HDFS/Hive ODS-DWD-DWS 数仓、TF-IDF + Logistic Regression 三分类、5 折 OOF 正式预测、MySQL serving、FastAPI、React/ECharts 情感作战室，以及基于 DeepSeek 的只读分析 Agent。

## 1. 最终生产基线

| 项目 | 当前值 |
|---|---|
| 数据范围 | Amazon Fashion production-v1 实验子集 |
| 批次 | `prod_v1_100k` |
| ODS 评论 | 100,000 |
| DWD 有效评论 | 99,703 |
| 商品数 | 76,784 |
| NLP 输入唯一键 | 99,703 |
| 正式预测方式 | 5-fold Stratified Out-of-Fold |
| 正式模型版本 | `tfidf_logreg_oof_v1` |
| OOF 覆盖率 | 100% |
| serving 版本 | `prod_v2` / schema `serving_v2` |
| MySQL 数据库 | `shopreview_serving` |
| 规则抽取 | `keyword_rules_v1` |
| API | `http://127.0.0.1:8080` |
| 大屏 | `http://127.0.0.1:5173` |

当前 OOF 预测分布为 positive 64,861、neutral 18,943、negative 15,899；平均预测置信度为 0.753397。以上模型预测不等同于人工标注真值。

## 2. 系统架构

```text
Amazon Fashion JSONL
        │  标准库逐行解析、限定范围
        ▼
HDFS → Hive ODS → Hive DWD
                    │
                    ├─ 99,703 条清洗评论 → NLP 输入
                    │                     ├─ 留出测试评估
                    │                     ├─ 5 折 OOF 正式预测
                    │                     └─ 全量模型仅供新评论推理
                    │
                    ▼
             Hive 情感 DWD / DWS
                    │
                    ▼
          MySQL shopreview_serving
                    │  agent_reader 只读查询
                    ▼
              FastAPI :8080
               ├─ React/ECharts 大屏 :5173
               └─ DeepSeek Agent 白名单工具
```

仓库已裁剪为生产运行版本，不包含本地 JSON 数据回退、阶段运行器、合成阶段表或相应测试夹具。生产 API 只查询配置批次与模型版本。

## 3. 快速启动

### 3.1 前置条件

- Windows PowerShell；
- Docker 中已有 `shopreview_mysql`，数据库为 `shopreview_serving`；
- 项目根目录已有 `.venv`；
- `dashboard/node_modules` 已安装；
- `backend/.env` 中保存现有 `agent_reader` 只读凭据；
- 如使用 AI 调查，`agent/.env` 中保存有效 DeepSeek Key。

所有本地 `.env` 均被 Git 忽略，不得把密码或 Key 写入代码、文档或提交历史。

### 3.2 启动后端

```powershell
cd D:\bdt-app-course\projects\ShopReview_NLP_Agent
.\backend\start_warehouse.bat
```

启动前的只读数据库检查：

```powershell
.\.venv\Scripts\python.exe backend\scripts\check_mysql_serving.py
```

### 3.3 启动前端

另开 PowerShell：

```powershell
cd D:\bdt-app-course\projects\ShopReview_NLP_Agent\dashboard
.\node_modules\.bin\vite.cmd --host 127.0.0.1
```

访问：

- Swagger：`http://127.0.0.1:8080/docs`
- 情感作战室：`http://127.0.0.1:5173`

## 4. 生产指标

| 指标 | 当前值 |
|---|---:|
| 评论量 | 99,703 |
| 商品数 | 76,784 |
| 正面预测 | 64,861（65.05%） |
| 中性预测 | 18,943（19.00%） |
| 负面预测 | 15,899（15.95%） |
| 平均评分 | 4.0563 |
| 平均预测置信度 | 0.753397 |

serving v2 包含总览、日/月趋势、商品、品类、店铺、认证购买、星级矩阵、置信度、告警、脱敏样例、方面和负面原因共 13 张表。

## 5. 目录说明

```text
agent/      DeepSeek 编排、系统提示词和 16 个白名单工具
backend/    FastAPI、参数化 MySQL 查询与只读 provider
dashboard/  React + TypeScript + ECharts 情感作战室
data/       本地处理数据；生成物均被 Git 忽略
docs/       数据字典、契约、训练报告和生产验收文档
reports/    可提交的安全摘要与 manifest
scripts/    有界检查及 production-v1 数仓/NLP运行器
sql/        production ODS、DWD、DWS 与校验 SQL
src/data/   流式转换、导出和预测契约校验
tests/      仅使用临时合成记录的生产处理单元测试
```

## 6. 安全与数据边界

- 商品主键使用 `parent_asin`；店铺使用 `store_key`。
- API 固定过滤 `prod_v1_100k` 与 `tfidf_logreg_oof_v1`。
- MySQL 查询使用参数化 SQL；表名只允许来自代码内固定白名单。
- 后端拒绝使用 MySQL `root`，应用账号必须为只读 `agent_reader`。
- 前端不直连 Hive/MySQL，不包含 mock 业务数据。
- Agent 不执行 SQL、不修改仓库、不读取原始 JSONL。
- 评论样例只返回 `review_text_preview`，不返回 `user_id` 或完整文本。
- 方面和负面原因来自关键词规则，不得描述为 LLM 抽取。

## 7. 验证

```powershell
# Python 单元测试
.\.venv\Scripts\python.exe -m unittest discover -s tests\data -v

# Agent/warehouse 连通
$env:PYTHONPATH=(Get-Location).Path
.\.venv\Scripts\python.exe -m agent.scripts.ping_kpi

# 前端生产构建
cd dashboard
npm.cmd run build
```

当前裁剪版本验证：Python 38/38 PASS，前端 build PASS，API `/docs`、`/api/kpi`、好评店铺榜和好评商品榜均返回 HTTP 200。

## 8. 文档索引

- [最终生产验收报告](docs/PRODUCTION_SYSTEM_ACCEPTANCE_REPORT.md)
- [API 参考](docs/API_REFERENCE.md)
- [数据字典](docs/DATA_DICTIONARY.md)
- [有界数据检查报告](docs/DATA_INSPECTION_REPORT.md)
- [ODS/DWD 验收报告](docs/PRODUCTION_ODS_DWD_V1_REPORT.md)
- [NLP 输入交付与预测写回报告](docs/NLP_PRODUCTION_V1_HANDOFF_REPORT.md)
- [NLP 基线训练报告](docs/NLP_BASELINE_TRAINING_REPORT.md)
- [NLP 数仓契约](docs/NLP_WAREHOUSE_CONTRACT.md)
- [规则方面分析契约](docs/ASPECT_WAREHOUSE_CONTRACT.md)
