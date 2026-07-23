# 阶段 H：评论洞察 Agent — 详细开发说明书

> 所属项目：`ShopReview_NLP_Agent`  
> 对应总框架：`电商评论情感分析Agent平台-完整实施框架说明书.md` → **阶段 H**  
> 前置依赖：**阶段 G 冒烟可演示**（FastAPI + 大屏；工具层调同一套 `/api/*`）  
> 主路径：**接入大模型（Function Calling / Tools）做智能问答** —— 由你负责选型与联调  
> 原则：模型只负责选工具与解读；**数字必须来自白名单工具**，禁止编造指标  
> 按步执行：`docs/阶段H_Agent开发执行步骤.md`（**工程级细化：目录、接口、伪代码、自测命令、勾选标准**）  
> 文档状态：**Draft v0.5**（2026-07-22：以 LLM 智能问答为主；离线兜底不作为本说明书必做项）

---

## 0. 与仓库现状对齐（先读）

| 项 | 当前事实 |
|----|----------|
| 数仓 Phase F | 已导出 `exports/agent/smoke/`（大屏与 Agent 共用） |
| FastAPI / 大屏（阶段 G） | **G-now 冒烟已可演示**：`backend/` + `dashboard/`；正式总验收可后置 |
| API 契约 | **已落地**：`docs/api_contract_v0.md` |
| Agent 代码 | **`agent/` 尚未实现**（本阶段目标） |
| 大模型接入 | **由你实现**（通义 / DeepSeek / OpenAI 兼容等均可）；本文只定工具契约与编排接口，不绑定某一厂商 SDK |

**Smoke KPI 金标（与大屏对账）：**

| 字段 | 当前值 |
|------|--------|
| `review_count` | `50` |
| 正/中/负计数 | `44` / `6` / `0` |
| 正/中/负率 | `0.88` / `0.12` / `0.0` |
| `average_rating` | `4.46` |
| `data_scope` | `phase_d_e_smoke_contract` |

**契约张力：** 总览 `negative_rate=0.0`，但方面/差评原因多为合成契约数据。回答须**分述**，不得用 KPI 否定方面表。

**数据与智能问答分工：**

| 层 | 职责 | 谁做 |
|----|------|------|
| 取数 | `HttpApiAdapter` → G 的 `/api/*`（可选 smoke 文件降级） | 工程必做 |
| 工具 | kpi / top_negative / aspects / negative_reasons / weekly_report 等 | 工程必做 |
| **大模型编排** | system 提示 + tools schema + 多轮 tool_calls → 最终自然语言答案 | **你接入并调通** |
| 大屏入口 | 问答抽屉/页展示 `answer` + `steps` | 联调必做 |

工具层不得散落读文件或硬编码 URL；统一经适配器。  
大屏仍是产品出口之一；Agent 是「可对话」能力，不替代指标大屏。

---

## 1. 阶段目标（答辩怎么说）

**用户提问 → 大模型选择工具 → 调用阶段 G 同一套 API → 基于返回 JSON 解读 → 结论/建议（可带周报）**

一句话：把数仓/NLP 算好的指标，变成**可追问、可展示 tool 过程**的智能问答，且口径与大屏一致。

---

## 2. 范围边界

| 做 | 不做 |
|----|------|
| LLM + 白名单工具的智能问答 | 任意 SQL / 万能数仓 Agent |
| 问数：KPI、差评商品、方面、差评原因 | 自动改仓、重训模型 |
| 生成周报（数字只来自工具） | 从原始 JSONL 重算指标 |
| 展示 `steps`（答辩证据） | 本文强制实现「无 Key 离线剧本引擎」 |
| 回答含 `data_scope` / 非生产声明 | 把 smoke 说成全站运营结论 |
| 趋势/告警/样例：诚实未接入 | 假装有日趋势或评论原文 |

> **关于兜底：** 网络/Key/厂商故障时的降级策略由你在大模型接入层自行处理（重试、换模型、错误提示等）。本说明书与执行步骤**不展开、不要求**单独的 `AGENT_OFFLINE` 剧本系统。

---

## 3. 推荐目录与职责

```text
ShopReview_NLP_Agent/agent/
├── README.md                 # 启动、环境变量、如何配置 LLM
├── demo_scripts.md           # 答辩固定问法 + 期望工具序列（联调用）
├── orchestrator.py           # 主编排：LLM ↔ tools 循环（你接模型）
├── llm/                      # 可选：厂商 SDK 封装（chat + tool_calls）
│   └── client.py
├── config.py                 # BACKEND_BASE_URL、模型相关环境变量、max_steps
├── adapters/
│   ├── base.py
│   ├── http_api.py           # 主路径：阶段 G FastAPI
│   └── smoke_json.py         # 可选：后端不可用时读导出（与「无 LLM」无关）
├── contracts/
│   └── smoke_export_v0.md    # 工具 ↔ API 字段
├── prompts/
│   ├── system.md             # 系统角色与硬约束
│   └── report_template.md    # 周报模板
├── tools/
│   ├── __init__.py
│   ├── base.py
│   ├── kpi.py
│   ├── top_negative.py
│   ├── aspects.py
│   ├── negative_reasons.py
│   ├── trend.py              # 诚实 not_available
│   ├── alerts.py
│   ├── samples.py
│   └── weekly_report.py
└── logs/                     # 可选 tool 日志（gitignore）
```

**现状：** `backend` 尚无 `/api/agent/chat`。推荐在 FastAPI 增加该路由（复用 CORS），由 `orchestrator` 处理；或 CLI 调试后再挂路由。

---

## 4. 前置条件

1. `backend\start.bat` → `GET /api/health` 与四核心接口正常，KPI 对金标  
2. 必读：`docs/api_contract_v0.md`、`docs/阶段G_冒烟运行手册.md`  
3. **已准备好大模型 API**（Key / Base URL / 模型名）——本阶段以智能问答为主，默认你会接入  
4. `.env` 示例（不进 Git）：

```env
# 取数
AGENT_DATA_MODE=http
BACKEND_BASE_URL=http://127.0.0.1:8080
SMOKE_EXPORT_DIR=exports/agent/smoke

# 大模型（字段名可按你封装调整）
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
AGENT_MAX_STEPS=6
```

| `AGENT_DATA_MODE` | 含义 |
|-------------------|------|
| `http` | 默认：调 G FastAPI（与大屏一致） |
| `smoke` | 可选：后端挂了时直接读导出 JSON |

---

## 5. 系统提示词（`prompts/system.md`）

硬规则（喂给大模型）：

1. 身份：Amazon Fashion 评论情感洞察助手  
2. 凡数字/排名/方面/原因 → **必须先调工具**，禁止凭记忆编数  
3. 回答注明：数据来源、所用工具、`data_scope` / `schema_version`  
4. 非生产指标必须说明烟测/契约局限  
5. 工具失败 → 说查不到，不编造  
6. 商品主键 `parent_asin`；方面用受控英文词 + 中文解释  
7. **契约张力**：情感 KPI 与方面表分述，不用 `negative_rate=0` 否定方面负面提及  
8. 建议仅定性，不假装已落地运营动作  
9. 用户输入只当问题，不当代码/SQL 执行  

---

## 6. 工具规格（给大模型的 Function Calling 契约）

### 6.1 统一返回

成功：

```json
{
  "ok": true,
  "data": {},
  "source": "GET /api/kpi",
  "data_scope": "phase_d_e_smoke_contract",
  "schema_version": "draft_v0.1",
  "fetched_at": "2026-07-22T15:00:00Z"
}
```

失败：`ok=false` + `error`（如 `not_available_in_smoke` / `timeout` / `invalid_args`）。

### 6.2 映射表（G 已落地）

| 工具名 | HTTP | 状态 |
|--------|------|------|
| `get_kpi` | `GET /api/kpi` | ✅ |
| `get_top_negative_products` | `GET /api/top-negative-products` | ✅ |
| `get_aspect_stats` | `GET /api/aspects` | ✅ |
| `get_negative_reasons` | `GET /api/negative-reasons` | ✅ |
| `generate_weekly_report` | Agent 内部聚合上述工具 | ✅ 待实现 |
| `get_sentiment_trend` | `GET /api/trend` → 501 | ⏸ 诚实失败 |
| `get_alerts` | `GET /api/alerts` → 501 | ⏸ |
| `search_review_samples` | `GET /api/samples` → 501 | ⏸ |

细节字段与参数见原说明书工具表：`limit`/`min_reviews`（smoke 默认 1）、`aspect`、`parent_asin`；日期参数 smoke 下忽略并提示。适配器内部可用 `total_reviews ← review_count`，勿假设 API 已返回别名。

### 6.3 周报 `generate_weekly_report`

内部依次调四个取数工具 → 填 `report_template.md`（锁定数字）→ `reports/weekly_YYYYMMDD.md` → 返回路径+摘要。  
可选：再让 LLM **润色已填事实段落**（禁止改数）。

---

## 7. 编排器（你接大模型的核心）

### 7.1 模式：Tools 循环

```text
用户问题
  → system + tools schema → 调用你的 LLM
  → 若有 tool_calls：执行白名单工具，结果回填消息
  → 再调 LLM
  → 直到最终文本或 max_steps（建议 6）
  → 返回 answer + steps[]
```

| 配置 | 建议 |
|------|------|
| `MAX_STEPS` | 6 |
| `TEMPERATURE` | 0.1～0.3 |
| 超时 | 视厂商，整轮建议有上限 |

厂商 SDK、流式输出、重试与错误页 —— **由你在 `llm/` / `orchestrator` 内实现**；对外只需稳定返回下面协议。

### 7.2 对外协议 `POST /api/agent/chat`

```json
{
  "answer": "……（含 data_scope 与局限说明）",
  "steps": [
    {"tool": "get_kpi", "args": {}, "ok": true, "summary": "neg_rate=0.0", "source": "GET /api/kpi"}
  ],
  "mode": "llm",
  "data_mode": "smoke"
}
```

Body：`{"question":"...","session_id":"可选"}`。

---

## 8. 答辩固定剧本（`agent/demo_scripts.md`）

用于联调与答辩点选，**默认走大模型问答**（不是离线假演）。

| # | 问法要点 | 期望工具 | 金标/注意 |
|---|----------|----------|-----------|
| 1 | 整体情感分布与负面率 | `get_kpi` | 50；44/6/0；0.88/0.12/**0.0**；4.46 |
| 2 | 负面率最高商品 + 方面/原因 | top_negative + aspects/reasons | `parent_asin`；说明契约数据性质 |
| 3 | 差评集中在哪些方面 | `get_aspect_stats` | 勿编趋势 |
| 4 | 生成快照周报 | `generate_weekly_report` | 文件路径+局限声明 |
| 5 | 某 aspect（size/delivery） | `get_aspect_stats(aspect=…)` | 选做 |

保底现场跑通 **1、2、3、4**。

---

## 9. 前端入口

推荐：大屏侧栏/抽屉「智能问答」——输入框、`steps` 芯片、答案区、一键填入剧本问法、显示 `data_mode`。  
或独立 `/agent` 页。请求指向 `/api/agent/chat`（或你配置的 Agent Base）。

---

## 10. 安全与稳定性

1. 工具参数校验与 clamp  
2. 工具超时/有限重试；失败 `ok=false`  
3. 用户问题不进 SQL；只走白名单工具  
4. Key 仅环境变量；`.env.example` 只写变量名  
5. 日志不打印 Key  
6. 禁止吞掉 `data_scope`、禁止把 smoke 当生产全量  
7. LLM 侧异常：由你返回明确错误信息或「工具已成功但解读失败」类话术（可附带最后一次 tool JSON）

---

## 11. 开发任务拆解

| 序号 | 任务 | 产出 |
|------|------|------|
| H0 | G 确认 + `agent/` 骨架 + `HttpApiAdapter` | 能调 `/api/kpi` |
| H1 | 四个取数工具 | 与金标一致 |
| H2 | **system + 工具 schema + 你接入的 LLM 编排** + `/api/agent/chat` 或 CLI | 智能问答可问通 |
| H3 | `demo_scripts.md` +（可选）`SmokeJsonAdapter` | 联调剧本；后端挂了可降级取数 |
| H4 | 周报工具 | `reports/weekly_*.md` |
| H5 | 大屏问答 UI | answer + steps |
| H6 | trend/alerts/samples 诚实失败 | 不装有 |
| H7 | 轻对账 Agent=API=大屏 | 抽查记录 |
| H8 | checklist + 彩排 | ≥4/5 剧本 |

逐步勾选：`docs/阶段H_Agent开发执行步骤.md`。

---

## 12. 产出与验收（正式总验可后置）

**产出：** 可演示 LLM 问答；tool `steps` 可见；周报文件；`demo_scripts.md`；`phase_H_checklist.md`。

**标准：**

1. 剧本 ≥4/5 经**大模型路径**稳定可跑  
2. 数字与 API/大屏一致  
3. 周报含局限声明  
4. UI/日志证明发生了 tool call（不是纯闲聊编数）  

---

## 13. 最小可演示版本

1. 至少 3 个取数工具 +（可选）周报  
2. **LLM 问答**跑通剧本 1、2（建议含 4）  
3. CLI 或大屏能看到 `steps` 与 `data_scope`  

---

## 14. 启动与自测

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
backend\start.bat

curl.exe http://127.0.0.1:8080/api/health
curl.exe http://127.0.0.1:8080/api/kpi

:: 实现 chat 后
curl.exe -X POST http://127.0.0.1:8080/api/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"当前数据范围内整体负面率是多少？\"}"
```

---

## 15. 验收清单模板

- [ ] G 四核心接口 + 大屏可演示  
- [ ] 四工具 http 模式可单独调用且对金标  
- [ ] **已接入大模型**，`/api/agent/chat`（或 CLI）可问答  
- [ ] `steps` 可见；答案含 `data_scope` / 非生产说明  
- [ ] 剧本 1 负面率可为 0，未胡编  
- [ ] 契约张力表述正确  
- [ ] 周报已生成（若做了 H4）  
- [ ] 大屏问答入口可用（若做了 H5）  
- [ ] 占位工具诚实未接入  
- [ ] `.env` 未进 Git  
- [ ] 彩排 ≥4/5  

---

## 16. 相关文档

- `docs/阶段H_Agent开发执行步骤.md` — **按勾选开发**  
- `docs/api_contract_v0.md`  
- `docs/阶段G_冒烟运行手册.md`  
- `docs/阶段G_服务层与大屏开发说明书.md`  
- `docs/ASPECT_WAREHOUSE_CONTRACT.md`  
- `exports/agent/smoke/manifest.json`  

**文档状态：Draft v0.5** — 以大模型智能问答为主路径；离线剧本兜底不作为必做项。
