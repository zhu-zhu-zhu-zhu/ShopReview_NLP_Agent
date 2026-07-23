# 阶段 H：Agent 开发 — 详细执行步骤（工程级）

> **角色视角：** 高级 Agent 开发工程师按本文落地实现。  
> **目标：** 大模型 + 白名单工具 → 智能问答；数字与阶段 G `/api/*`、大屏完全同口径。  
> **规格：** `docs/阶段H_Agent开发说明书.md` v0.5  
> **HTTP 契约：** `docs/api_contract_v0.md`  
> **大模型：** 由你选型并接入（OpenAI 兼容 / 通义 / DeepSeek 等）；本文把 **tools 契约、编排闭环、挂载方式、联调标准** 写到可直接编码的粒度。  
> **不做：** 无 Key 离线剧本引擎（模型侧重试/报错由你自行处理）。

每做完一步，把对应 `- [ ]` 改成 `- [x]`。

---

## 0. 先建立心智模型（编码前 10 分钟）

### 0.1 数据流（必须画在脑子里）

```text
┌─────────────┐     POST /api/agent/chat      ┌──────────────────┐
│  Dashboard  │ ────────────────────────────► │ backend router   │
│  问答抽屉    │ ◄──── {answer, steps[]} ──── │ agent_chat.py    │
└─────────────┘                               └────────┬─────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │  orchestrator    │
                                              │  LLM ↔ tools 循环 │
                                              └────────┬─────────┘
                                                       │
                          ┌────────────────────────────┼────────────────────────────┐
                          ▼                            ▼                            ▼
                   ┌─────────────┐            ┌──────────────┐             ┌─────────────┐
                   │ llm/client  │            │ tools/*      │             │ prompts/    │
                   │ (你接入)     │            │ 白名单执行    │             │ system.md   │
                   └─────────────┘            └──────┬───────┘             └─────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │ adapters     │
                                              │ HttpApiAdapter│
                                              └──────┬───────┘
                                                     │ GET /api/kpi|products|aspects|...
                                                     ▼
                                              ┌──────────────┐
                                              │ Stage G API  │  :8080
                                              │ (已实现)      │
                                              └──────────────┘
```

**铁律：** LLM 永远不直接读 `exports/`、不直接算比率；只消费工具返回的 JSON。

### 0.2 分层职责（防止把逻辑糊在路由里）

| 层 | 目录 | 允许做什么 | 禁止做什么 |
|----|------|------------|------------|
| Router | `backend/app/routers/agent_chat.py` | 解析 body、调 orchestrator、返回 JSON | 调 LLM SDK、拼 prompt |
| Orchestrator | `agent/orchestrator.py` | 消息循环、调 LLM、调工具注册表、组装 steps | 写死 KPI 数字 |
| LLM | `agent/llm/` | 厂商 API、解析 tool_calls | 访问业务 HTTP |
| Tools | `agent/tools/` | 参数校验、调 adapter、统一包装 | 自己算数仓指标 |
| Adapter | `agent/adapters/` | HTTP 或读 smoke 文件 | 调 LLM |

### 0.3 Smoke KPI 金标（对账用，导出变更则以本机 JSON 为准）

| 字段 | 值 |
|------|-----|
| `review_count` | `50` |
| `positive_count` / `neutral_count` / `negative_count` | `44` / `6` / `0` |
| `positive_rate` / `neutral_rate` / `negative_rate` | `0.88` / `0.12` / `0.0` |
| `average_rating` | `4.46` |
| `data_scope` | `phase_d_e_smoke_contract` |

**契约张力：** 总览负面率可为 `0`，方面/原因仍是合成契约数据——回答必须分述，禁止用 KPI「打脸」方面表。

### 0.4 推荐编码顺序

```text
H0 取数适配器可跑
 → H1 四工具 + OpenAI tools JSON Schema
 → H2 编排 + 你接 LLM + /api/agent/chat
 → H3 答辩剧本文档
 → H4 周报工具
 → H6 占位工具（可与 H1 尾部一起做）
 → H5 大屏 UI
 → H7 对账 → H8 材料
```

---

## 总览检查表

| 步骤 | 名称 | 建议耗时 | 完成标志（一句话） |
|------|------|----------|-------------------|
| H0 | 环境 + 骨架 + HttpApiAdapter | 1～2 h | `python -m agent.scripts.ping_kpi` 打出 50 |
| H1 | 四取数工具 + Schema 注册表 | 2～3 h | 四工具单测 PASS + schema 可被 LLM 加载 |
| H2 | LLM + Orchestrator + Chat API | 核心 0.5～2 天 | curl 剧本 1：有 steps 且负面率=0 |
| H3 | demo_scripts + 可选 SmokeAdapter | 1 h | 五个问法写清；可选降级取数 |
| H4 | 周报 | 1～2 h | `reports/weekly_*.md` 数字锁死 |
| H5 | 大屏问答 UI | 2～4 h | 抽屉可见 answer+steps |
| H6 | 三占位工具 | 30～60 min | 问趋势得到 not_available |
| H7 | 轻对账 | 30 min | 三端数字一致 |
| H8 | checklist + 彩排 | 1 h | 剧本 1～4 连跑 |

---

## 步骤 H0：环境确认 + 仓库骨架 + HttpApiAdapter

### H0.1 启动并验证阶段 G（阻塞项）

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
backend\start.bat
```

另开终端（Windows 务必用 `curl.exe`，避免 PowerShell 别名）：

```bat
curl.exe -s http://127.0.0.1:8080/api/health
curl.exe -s http://127.0.0.1:8080/api/kpi
curl.exe -s "http://127.0.0.1:8080/api/top-negative-products?limit=3&min_reviews=1"
curl.exe -s http://127.0.0.1:8080/api/aspects
curl.exe -s "http://127.0.0.1:8080/api/negative-reasons?limit=3"
curl.exe -s -w "\nHTTP:%{http_code}\n" http://127.0.0.1:8080/api/trend
```

勾选：

- [x] health：`data_mode=smoke`，`production_business_metrics=false`
- [x] kpi：与 §0.3 金标一致（注意 API 包装为 `{ok,data,meta}`，数字在 `data` 内）
- [x] trend：`HTTP:501` 且 `error=not_available_in_smoke`
- [ ] 大屏 `http://127.0.0.1:5173` 能刷出同一套 KPI（可选但推荐）

若 8080 连不上：先看 `docs/阶段G_冒烟运行手册.md`，不要继续写 Agent。

> **2026-07-22 H0 PASS：** `agent/` 骨架 + `HttpApiAdapter` + `python -m agent.scripts.ping_kpi` → `PING_KPI_OK`（review_count=50, negative_rate=0.0）；trend → `not_available_in_smoke`。

### H0.2 目标目录树（一次建齐空文件即可）

在仓库根创建：

```text
agent/
├── README.md                 # H8 再写全；H0 可先写三行「WIP」
├── __init__.py
├── config.py                 # 读环境变量
├── orchestrator.py           # H2 再填
├── .env.example
├── adapters/
│   ├── __init__.py
│   ├── base.py               # 抽象接口 + ToolResult 类型
│   ├── http_api.py           # H0 必做
│   └── smoke_json.py         # H3 可选
├── tools/
│   ├── __init__.py           # 注册表 TOOL_REGISTRY / get_openai_tools()
│   ├── base.py               # clamp、wrap、日志
│   ├── kpi.py                # H1
│   ├── top_negative.py       # H1
│   ├── aspects.py            # H1
│   ├── negative_reasons.py   # H1
│   ├── weekly_report.py      # H4
│   ├── trend.py              # H6
│   ├── alerts.py             # H6
│   └── samples.py            # H6
├── llm/
│   ├── __init__.py
│   └── client.py             # H2：你接厂商
├── prompts/
│   ├── system.md             # H2
│   └── report_template.md    # H4
├── contracts/
│   └── smoke_export_v0.md    # H8 可补
├── scripts/
│   ├── __init__.py
│   └── ping_kpi.py           # H0 自测入口
└── logs/                     # gitignore；可选写 tool 日志
```

Python 导入约定：从**仓库根**运行，例如：

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
set PYTHONPATH=%CD%
.venv\Scripts\python.exe -m agent.scripts.ping_kpi
```

或在 `backend` 挂载时把仓库根加入 `sys.path`（H2.4 写明）。

### H0.3 环境变量

**`agent/.env.example`（可提交）：**

```env
AGENT_DATA_MODE=http
BACKEND_BASE_URL=http://127.0.0.1:8080
SMOKE_EXPORT_DIR=exports/agent/smoke
HTTP_TIMEOUT_SEC=15

LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
AGENT_MAX_STEPS=6
AGENT_TEMPERATURE=0.2
```

**本地 `agent/.env` 或仓库根 `.env`：** 填真实 Key；确认 `.gitignore` 已忽略 `.env`（本仓库已有）。

`config.py` 建议职责：

- 用 `python-dotenv` 加载 `.env`（可选依赖；也可手动读）
- 提供 `Settings`：`backend_base_url`（去尾 `/`）、`data_mode`、`llm_*`、`max_steps`、`timeout`
- `repo_root()`：定位 `exports/agent/smoke` 相对路径

勾选：

- [x] `.env.example` 已提交  
- [x] 本地 `.env` 存在且未 staged  

### H0.4 实现 `adapters/base.py`（建议类型）

统一工具/适配器结果（编排器与 LLM 都吃这一套）：

```python
# 逻辑形状（可 TypedDict 或 dataclass）
{
  "ok": True,
  "data": {},                      # 或 list
  "source": "GET /api/kpi",
  "data_scope": "phase_d_e_smoke_contract",
  "schema_version": "draft_v0.1",
  "production_business_metrics": False,
  "fetched_at": "2026-07-22T08:00:00+00:00",  # ISO8601
  "error": None,                   # 失败时字符串
  "message": None                  # 人类可读
}
```

抽象适配器建议方法（命名可微调，但语义要齐）：

| 方法 | 对应 API |
|------|----------|
| `get_health()` | `/api/health` |
| `get_kpi()` | `/api/kpi` |
| `get_top_negative_products(limit, min_reviews)` | `/api/top-negative-products` |
| `get_aspects(aspect=None)` | `/api/aspects` |
| `get_negative_reasons(limit, parent_asin=None)` | `/api/negative-reasons` |
| `get_trend()` / `get_alerts()` / `get_samples()` | 占位，可直接调 501 |

### H0.5 实现 `adapters/http_api.py`（本步核心代码）

行为规格：

1. `base_url = settings.backend_base_url`，例如 `http://127.0.0.1:8080`
2. 使用 `httpx` 或 `urllib.request`（推荐 `httpx`，加入 `backend/requirements.txt` 或 `agent/requirements.txt`）
3. `GET` + `timeout=HTTP_TIMEOUT_SEC`
4. **HTTP 200 且 body.ok=true**：把 `data` 放入结果；从 `meta` 拷贝 `data_scope` / `schema_version` / `production_business_metrics`；`source=f"GET {path}"`
5. **HTTP 501 / 400 / 500**：`ok=false`，`error` 优先取 body.error，否则 `http_{status}`
6. **连接失败**：`ok=false`，`error=upstream_unavailable`，`message` 含「请先启动 backend\\start.bat」
7. 不要吞掉异常变成假成功数据

`scripts/ping_kpi.py` 最小逻辑：

```text
adapter = HttpApiAdapter()
r = adapter.get_kpi()
assert r["ok"] and r["data"]["review_count"] == 50
print("PING_KPI_OK", r["data"]["negative_rate"], r["data_scope"])
```

勾选：

- [x] `HttpApiAdapter.get_kpi()` 金标通过  
- [x] 故意关掉后端再调一次 → `ok=false`（不是抛未捕获异常到顶）  

**H0 完成标志：** 不经过 LLM，Http 适配器稳定读 G。 ✅

---

## 步骤 H1：四个取数工具 + 注册表 + Function Calling Schema

> 目标：LLM 看到的「函数定义」与 Python 执行器一一对应；参数非法时工具自己挡掉。

### H1.1 `tools/base.py` 公共能力

实现建议：

| 函数 | 行为 |
|------|------|
| `clamp_int(v, lo, hi, default)` | 缺省/非法 → default；超出 → clamp |
| `now_iso()` | UTC 或本地 ISO 时间 |
| `summarize_for_step(tool, result)` | 从 result 抽短摘要，供 `steps[].summary`（如 `neg_rate=0.0, n=50`） |
| `get_adapter()` | 按 `AGENT_DATA_MODE` 返回 Http 或 Smoke 实例 |

可选：每次工具调用 append 一行 JSONL 到 `agent/logs/tools.jsonl`（注意不要写 API Key）。

### H1.2 四个工具的执行语义

#### （1）`get_kpi`

| 项 | 规格 |
|----|------|
| 描述（给 LLM） | 获取当前导出范围内评论情感总览 KPI（评论量、正中负数量与比率、均分）。无真实日历趋势。 |
| 参数 | 无必填；可选 `start_date`/`end_date`（YYYY-MM-DD）。smoke 下适配器/API 会忽略时间窗——工具层可原样转发，**不要因有日期就失败**。 |
| 成功 data | 与 `/api/kpi` 的 `data` 一致 |
| 自测 | `review_count==50`，`negative_rate==0.0` |

#### （2）`get_top_negative_products`

| 项 | 规格 |
|----|------|
| 描述 | 按负面率等排序的差评商品列表；主键为 parent_asin。 |
| 参数 | `limit` 默认 5，范围 1～20；`min_reviews` **smoke 默认 1**（生产以后可默认 20，用配置区分） |
| 成功 data | array |
| 自测 | `len>=1`，元素含 `parent_asin` |

#### （3）`get_aspect_stats`

| 项 | 规格 |
|----|------|
| 描述 | 方面/原因聚合；aspect 为受控英文词（size/material/delivery/…）。 |
| 参数 | 可选 `aspect`；若传入不在词表内 → `ok=false, error=invalid_args` **或** 忽略过滤并 message 提示（二选一写进 README，推荐 **invalid_args**） |
| 受控词 | `size,color,material,comfort,workmanship,description_mismatch,packaging,delivery,price,other` |
| 自测 | 无过滤非空；`aspect=size` 时每条 aspect 均为 size |

#### （4）`get_negative_reasons`

| 项 | 规格 |
|----|------|
| 描述 | 商品×差评原因明细。 |
| 参数 | `limit` 默认 10，1～50；可选 `parent_asin` |
| 自测 | 非空；过滤 parent_asin 时只返回该商品 |

### H1.3 OpenAI 风格 tools schema（必须可被你的客户端直接使用）

在 `tools/__init__.py` 提供：

- `TOOL_HANDLERS: dict[str, Callable]`
- `def openai_tools() -> list[dict]`：返回 Responses/Chat Completions 的 `tools` 数组
- `def run_tool(name: str, arguments: dict) -> dict`：查表执行；**未知 name → ok=false, error=unknown_tool**

每个 tool 的 JSON Schema 示例骨架（名称必须与 handler 一致）：

```json
{
  "type": "function",
  "function": {
    "name": "get_kpi",
    "description": "……",
    "parameters": {
      "type": "object",
      "properties": {
        "start_date": {"type": "string", "description": "可选 YYYY-MM-DD，smoke 下可能被忽略"},
        "end_date": {"type": "string"}
      },
      "additionalProperties": false
    }
  }
}
```

`get_top_negative_products` 的 properties 至少含 `limit`、`min_reviews`（integer）。  
`get_aspect_stats` 含 `aspect`（string）。  
`get_negative_reasons` 含 `limit`、`parent_asin`。

### H1.4 自测脚本建议 `agent/scripts/tools_smoke.py`

```text
对每个工具：
  r = run_tool(...)
  print(name, r["ok"], summarize(...))
  assert r["ok"]
对 get_kpi 断言金标
故意 run_tool("not_a_tool", {}) → ok=false
故意 aspect="物流" → invalid_args（若你选了严格模式）
```

```bat
set PYTHONPATH=%CD%
.venv\Scripts\python.exe -m agent.scripts.tools_smoke
```

勾选：

- [x] 四工具 PASS  
- [x] `openai_tools()` 返回 ≥4 个 function  
- [x] 未知工具 / 非法 aspect 行为符合你的 README 约定  

> **2026-07-22 H1 PASS：** `python -m agent.scripts.tools_smoke` → `TOOLS_SMOKE_OK`（KPI 金标、aspect=size 过滤、非法「物流」→`invalid_args`、未知工具→`unknown_tool`）。

**H1 完成标志：** 工具层可单测；已具备给 LLM 的 schema。 ✅

---

## 步骤 H2：接入大模型 + Orchestrator + `/api/agent/chat`（核心）

> 本步是阶段 H 的产品闭环。取数已在 H1 完成；这里只解决「模型怎么合法地用工具说话」。

### H2.1 写死 `prompts/system.md`（建议直接可粘贴的要点）

文件用中文即可，必须覆盖：

1. 你是 Amazon Fashion **评论情感洞察**助手，不是通用闲聊机器人。  
2. 任何数字、排名、方面、原因、比率 → **先调用工具**；禁止用训练记忆编造。  
3. 回答末尾固定包含：`data_scope`、是否生产业务指标、本次用过的工具名。  
4. 当前多为 smoke 契约数据：`production_business_metrics=false`，不得说成全站运营结论。  
5. 商品用 `parent_asin`；方面词用英文受控词，可括注中文（如 delivery≈物流相关）。  
6. **契约张力：** 总览 `negative_rate` 可能为 0，同时方面表仍有「负面提及」——必须说明两套数据性质不同，禁止互相否定。  
7. 工具 `ok=false` → 如实告知「当前查不到/未接入」，不要补全假表。  
8. 运营建议只能基于工具结果做定性建议。  

加载方式：`Path(__file__).parent / "prompts/system.md").read_text(encoding="utf-8")`。

勾选：

- [x] `system.md` 已存在且被 orchestrator 读取  

### H2.2 `llm/client.py`（你实现的接口约定）

对外请收敛成稳定接口，便于换厂商：

```python
class LLMClient:
    def chat(self, messages: list[dict], tools: list[dict] | None) -> LLMResponse:
        """
        返回：
          - content: str | None          # 最终文本（可能为空，若只有 tool_calls）
          - tool_calls: list[ToolCall]   # [{id, name, arguments: dict}]
          - raw: 任意                    # 可选，调试用
        """
```

实现要点（高级工程实践）：

| 点 | 建议 |
|----|------|
| 认证 | 只从 env 读 Key；禁止写进代码 |
| Base URL | 兼容代理 / 国内网关 |
| tools 格式 | 与 H1 `openai_tools()` 一致；若厂商格式不同，在 client 内转换 |
| arguments | 厂商常给 **字符串 JSON**，client 内 `json.loads`，失败则 tool 层 `invalid_args` |
| 超时 | 单次 LLM 请求超时（如 60s）与整轮编排超时分开 |
| 日志 | 打 model、耗时、tool_call 名；**禁止**打完整 Key；可选截断超长 content |
| 错误 | 网络/401/429 → 抛专用异常或返回结构化错误，由 orchestrator 转成用户可读 `answer` |

勾选：

- [x] 用最小 messages（无 tools）能打通「你好」类回复（证明 Key 有效）  
- [x] 带 tools 的请求能返回至少一个 `tool_calls`（可用剧本 1 问题试）  

### H2.3 `orchestrator.py` 状态机（按此实现，避免写飞）

**输入：** `question: str`，可选 `session_id`（首版可不做多轮历史）。  
**输出：**

```json
{
  "answer": "string",
  "steps": [
    {
      "tool": "get_kpi",
      "args": {},
      "ok": true,
      "summary": "review_count=50, negative_rate=0.0",
      "source": "GET /api/kpi"
    }
  ],
  "mode": "llm",
  "data_mode": "smoke",
  "error": null
}
```

**伪代码（必须遵守 max_steps）：**

```text
messages = [
  {role: system, content: system.md},
  {role: user, content: question}
]
steps = []
for i in 1..MAX_STEPS:
    resp = llm.chat(messages, tools=openai_tools())
    if resp.tool_calls:
        # 把 assistant tool_calls 消息按厂商格式 append 进 messages
        for call in resp.tool_calls:
            result = run_tool(call.name, call.arguments)
            steps.append({tool, args, ok, summary, source})
            # 把 tool 角色消息 append：content = json.dumps(result, ensure_ascii=False)
        continue
    else:
        answer = resp.content or ""
        # 可选守卫：若问题像问数但 steps 为空，追加一条 user「必须先调用工具」再重试一轮（计入 steps 预算）
        return success(answer, steps)

return {
  answer: "已达到最大工具步数，请缩小问题范围。以下是已查询到的工具结果摘要：…",
  steps,
  error: "max_steps_exceeded"
}
```

**守卫建议（强烈建议做）：**

- 用户问题匹配 `(多少|比率|负面|KPI|排行|方面|周报)` 且首轮无 tool_calls → 强制重试 1 次  
- 最终 answer 若完全不含数字但 steps 里有 KPI → 可在服务端用模板补一句「工具显示负面率为 0.0」（可选；优先靠 prompt）  

勾选：

- [x] `max_steps` 在编排循环中生效（代码已实现）  
- [x] steps 顺序与真实调用一致  
- [x] tool 原始 JSON 回传给模型（不要只回 summary）  

### H2.4 挂载 `POST /api/agent/chat`（推荐）

**为什么挂 backend：** 与大屏同源 `8080`、CORS 已配好、答辩只开一个 API 进程。

建议新增：

```text
backend/app/routers/agent_chat.py
```

并在 `backend/app/main.py`：`app.include_router(agent_chat.router)`。

路由规格：

| 项 | 值 |
|----|-----|
| Method/Path | `POST /api/agent/chat` |
| Body | `{"question": "……", "session_id": "可选"}` |
| question 空 | `400` + `ok:false` + `error=invalid_args` |
| 成功 | `200` + 上文 orchestrator 输出（可再包一层 `ok:true`） |
| LLM 失败 | `200` 或 `502`：`answer` 说明失败原因，`steps` 保留已成功工具结果，`error=llm_error` |

**路径问题：** uvicorn 的 `--app-dir backend` 时，确保能 `import agent`：

- 方案 A：在 `agent_chat` 路由里把仓库根插入 `sys.path`  
- 方案 B：把 `agent` 包放到可编辑安装 `pip install -e .`（需 pyproject；可选）  
- 方案 C：独立进程 `uvicorn` 跑 agent 服务（大屏改 `VITE_AGENT_BASE`）——答辩多开一个窗，次优  

首版推荐 **方案 A**，改动最小。

自测：

```bat
curl.exe -s -X POST http://127.0.0.1:8080/api/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"当前数据范围内，整体评论情感分布和负面率是多少？\"}"
```

验收（剧本 1）：

- [x] HTTP 200  
- [x] `steps` 中至少一次 `get_kpi` 且 `ok=true`  
- [x] `answer` 出现评论量 50、负面率 0（0% / 0.0 均可）  
- [x] `answer` 出现 `phase_d_e_smoke_contract` 或明确「非生产/烟测」  
- [x] **不出现**「负面率约 30%」这类幻觉  

另测：

```bat
curl.exe -s -X POST http://127.0.0.1:8080/api/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"\"}"
```

- [x] 400 或 ok=false（空 question → FastAPI 422/400）  

> **2026-07-22 H2 PASS：** DeepSeek `deepseek-v4-flash` + `orchestrator` + `POST /api/agent/chat`；`chat_smoke` / HTTP 剧本 1 均调用 `get_kpi`，负面率 0.0，含 data_scope / 非生产声明。

**H2 完成标志：** 大模型智能问答主路径闭环。 ✅

---

## 步骤 H3：答辩剧本文档 +（可选）Smoke 取数降级

### H3.1 编写 `agent/demo_scripts.md`（给自己和答辩用）

每个剧本固定四段：**问法 / 期望工具 / 金标或要点 / 失败时不应出现的说法**。

#### 剧本 1 — 总览 KPI

- 问：`当前数据范围内，整体评论情感分布和负面率是多少？`  
- 期望工具：`get_kpi`  
- 金标：50；44/6/0；0.88/0.12/**0.0**；4.46  
- 不应：编造非零负面率；说「近 7 天对比」却无趋势工具成功  

#### 剧本 2 — 差评商品 + 方面/原因

- 问：`负面率最高的几个商品是什么？主要差在哪些方面或原因？`  
- 期望：`get_top_negative_products` + `get_aspect_stats` 和/或 `get_negative_reasons`  
- 要点：说出至少 1 个 `parent_asin`；说明方面/原因为契约合成数据；可提及 smoke 下 `min_reviews=1`、单商品评论量可能很小  
- 不应：用「总览负面率是 0，所以不存在差评方面」这种逻辑  

#### 剧本 3 — 方面分布

- 问：`目前差评主要集中在哪些方面（如尺码、材质、物流相关）？`  
- 期望：`get_aspect_stats`  
- 要点：列出受控英文 aspect + 中文；说明烟测  
- 不应：声称「较上周上升」  

#### 剧本 4 — 周报

- 问：`请基于当前导出数据生成评论情感分析周报（快照版）。`  
- 期望：`generate_weekly_report`（H4 完成后）  
- 要点：返回文件路径；摘要 3～5 条；局限声明  

#### 剧本 5 — 单方面（选做）

- 问：`size（尺码）方面的负面提及情况怎样？`  
- 期望：`get_aspect_stats` 带 `aspect=size`  

勾选：

- [ ] `demo_scripts.md` 五幕写齐  
- [ ] 用 curl/UI 对剧本 1、2 至少各跑通一次（2 可在 H1 工具齐后、H4 前先跑）  

### H3.2（可选）`SmokeJsonAdapter`

**何时做：** 演示中途 G 进程挂了，仍想让工具取数成功（模型仍在线）。

实现要点：

- 根目录：`settings.smoke_export_dir` → `exports/agent/smoke`
- 读 `sentiment_overview.json` 等，取 `records`
- KPI：`records[0]`
- 列表类：内存过滤/排序（top_negative：按 `negative_rate` 降序；aspect 过滤；limit）
- `source` 写成 `smoke:sentiment_overview.json` 等形式
- `get_trend` 等直接 `ok=false, error=not_available_in_smoke`（不要读不存在的文件假装成功）

切换：`AGENT_DATA_MODE=smoke` 后重跑 `tools_smoke.py`。

勾选：

- [ ] （可选）smoke 模式金标 PASS  
- [ ] （可选）http↔smoke 切换无需改工具代码（只换 adapter）  

**H3 完成标志：** 联调问法固定；取数降级按需。

---

## 步骤 H4：周报工具（数字锁定）

### H4.1 `prompts/report_template.md` 建议结构

```markdown
# 评论情感分析周报（导出快照）

> 生成时间：{{generated_at}}
> data_scope：{{data_scope}}
> production_business_metrics：{{production_business_metrics}}

## 1. 总览
- 评论量：{{review_count}}
- 正面/中性/负面：{{positive_count}} / {{neutral_count}} / {{negative_count}}
- 比率：{{positive_rate}} / {{neutral_rate}} / {{negative_rate}}
- 均分：{{average_rating}}

## 2. 差评商品 TOP
{{product_table}}

## 3. 方面与原因
{{aspect_section}}

## 4. 说明与局限
- 本报告数字仅来自工具查询结果，未手工改数。
- 当前为烟测/契约范围时，不得解读为全站运营结论。
- 情感总览与方面契约数据性质可能不同，解读时已分述。
```

占位符用 `str.replace` 或 `Template` 即可；**不要**让 LLM 生成表格里的数字。

### H4.2 `tools/weekly_report.py`

算法：

1. `kpi = run_tool("get_kpi", {})`；失败则整报失败  
2. `products = run_tool("get_top_negative_products", {"limit": 5, "min_reviews": 1})`  
3. `aspects = run_tool("get_aspect_stats", {})`  
4. `reasons = run_tool("get_negative_reasons", {"limit": 10})`  
5. 渲染模板 → 写入仓库根 `reports/weekly_YYYYMMDD.md`（目录不存在则创建）  
6. 返回 `data: {path, summary_bullets: [...], kpi_snapshot: {...}}`  

注册进 `TOOL_HANDLERS` 与 `openai_tools()`。

可选：返回后再让 LLM 只润色「建议」段落——**传入已渲染 Markdown，并 system 写明禁止改数字**。首版可不做润色。

勾选：

- [ ] 直接 `run_tool("generate_weekly_report", {})` 生成文件  
- [ ] 文件内 `review_count` 为 50，`negative_rate` 为 0.0  
- [ ] 经 chat 问剧本 4，`steps` 含该工具，`answer` 含路径  

**H4 完成标志：** 周报可复现、可对账。

---

## 步骤 H5：大屏智能问答 UI（产品化）

> **2026-07-22 H5 PASS：** 顶栏「智能问答」侧抽屉；剧本芯片；`POST /api/agent/chat`；steps + answer + 原始 JSON；`npm run build` 通过。

### H5.1 交互规格（推荐抽屉，不新开站点）

在现有 `dashboard/`（Vite + React）增加：

| UI 元素 | 行为 |
|---------|------|
| 入口按钮 | 顶栏「智能问答」打开侧抽屉 |
| 快捷芯片 | 剧本 1～4 问法一键填入输入框 |
| 输入框 + 发送 | Enter 发送；请求中 disable |
| Steps 区 | 每个 step 一枚芯片：`tool` + `ok` 色点 + `summary` |
| Answer 区 | 纯文本或简易 Markdown |
| 错误 | 展示 `error` / `answer`；可「展开 JSON」看原始响应 |
| 状态 | 显示 `data_mode`（可从 `/api/health` 或 chat 响应读取） |

### H5.2 前端 API

`dashboard/.env` 已有 `VITE_API_BASE=http://127.0.0.1:8080`。

```ts
// 示意
POST `${VITE_API_BASE}/api/agent/chat`
Body: { question: string }
```

注意：

- 超时调长（模型+多轮工具可能 30～90s）  
- CORS：backend 已允许 5173；若独立 Agent 端口，需加 origins  

### H5.3 视觉约束

延续现有企业风大屏，**不要**另起紫色 AI 聊天套皮；抽屉宽度约 380～420px；steps 用现有 badge 色系。

勾选：

- [x] 先起 backend 再 dashboard，抽屉问剧本 1 成功  
- [x] Network 面板确认打到 `8080/api/agent/chat`  
- [x] steps 与 curl 一致  

> **2026-07-22 H5 PASS：** 顶栏抽屉 + 剧本芯片；`/api/agent/chat` 使用 **in-process** 取数（避免同进程嵌套 HTTP 502）。抽屉实测可打开；HTTP 剧本 1 → `get_kpi` + 负面率 0.0。

**H5 完成标志：** 答辩可只开浏览器完成「看数 + 提问」。 ✅

---

## 步骤 H6：占位工具（与大屏能力条对齐）

三个工具：`get_sentiment_trend`、`get_alerts`、`search_review_samples`。

两种实现（选一，推荐 A）：

| 方案 | 做法 |
|------|------|
| A | HttpAdapter 调 `/api/trend|alerts|samples`，把 501 body 转成工具 `ok=false` |
| B | 工具内直接返回 `error=not_available_in_smoke`，不发 HTTP |

描述里写清「当前 smoke 无日趋势/告警/评论文本；禁止编造」。

注册进 schema，让模型在用户问「最近一周趋势」时能选到它并得到失败结果，再如实回答。

勾选：

- [x] 三工具可调用且 ok=false  
- [x] chat：「最近差评趋势如何？」→ 答案含「暂未接入/无趋势数据」  
- [x] 代码检索无读取 `data/raw` JSONL  

> **2026-07-22 H6 PASS（方案 A）：** `get_sentiment_trend` / `get_alerts` / `search_review_samples` 经 `HttpApiAdapter` 调 `/api/trend|alerts|samples` → `not_available_in_smoke`（source=`GET /api/...`）。`placeholders_smoke` OK；chat 问趋势会调 `get_sentiment_trend` 并诚实说明无日趋势。

**H6 完成标志：** 诚实能力边界。 ✅

---

## 步骤 H7：轻对账清单（开发自测）

对同一时刻数据：

| # | 检查 | 方法 | PASS |
|---|------|------|------|
| 1 | KPI | chat 答案 vs `curl /api/kpi` vs 大屏 KPI 条 | ☐ |
| 2 | Top1 parent_asin | chat vs `curl top-negative-products?limit=1` | ☐ |
| 3 | aspects size | chat 问 size vs `curl /api/aspects?aspect=size` 条数 | ☐ |
| 4 | 周报 | 文件数字 vs kpi 金标 | ☐ |
| 5 | 局限声明 | answer 含 data_scope 或非生产 | ☐ |
| 6 | 契约张力 | 剧本 2 未用负率 0 否定方面 | ☐ |
| 7 | steps 真实性 | 任意一次问答 steps 非空且 tool 名在白名单 | ☐ |

把结果记入 `docs/phase_H_checklist.md` 日期节。

**H7 完成标志：** 无口径冲突（非正式总验）。

---

## 步骤 H8：交付物与彩排

### H8.1 文档交付

- [ ] `docs/phase_H_checklist.md`（从规格书验收清单复制并勾选）  
- [ ] `agent/README.md` 必须包含：  
  - 启动顺序（先 G API，再问答）  
  - 环境变量表  
  - 你用的模型厂商与 `LLM_*` 示例  
  - `PYTHONPATH` / 如何跑 `tools_smoke`  
  - 已知限制（smoke、无趋势）  
- [ ] `agent/contracts/smoke_export_v0.md`：工具名 ↔ path 一页表  
- [ ] （可选）`reports/` 下放一张问答截图 `agent_chat_smoke.png`  

### H8.2 彩排脚本（计时）

1. 开 `backend\start.bat` + `dashboard\start.bat`  
2. 大屏指 KPI → 打开问答 → 剧本 1～4 各一次  
3. 故意问趋势 → 展示诚实失败  
4. 开场口述：「模型只选工具；数来自与大屏同一 API；当前是烟测契约数据。」  

- [ ] 剧本 1～4 连续成功（≥4/5）  
- [ ] 全程无 Key 泄露到屏幕/录屏  

正式总验（G 步骤 7 + 本清单）建议结项前统一做。

**H8 完成标志：** 阶段 H 开发可宣布完成，待结项总验。

---

## 依赖与工程卫生

### Python 依赖建议

在 `agent/requirements.txt` 或并入根/后端 requirements：

```text
httpx>=0.27
python-dotenv>=1.0
# 再加你的 LLM 官方 SDK，例如：
# openai>=1.40
```

### Git

- 提交：`agent/` 代码、prompt、demo_scripts、docs  
- **禁止提交：** `.env`、`agent/logs/*`、真实 Key  
- `reports/weekly_*.md` 可提交一份样例便于答辩  

### 日志与隐私

- 不落盘用户以外的原始评论全文（本阶段本无样例）  
- tool 日志可只留 summary  

---

## 明确不做

| 不做 | 原因 |
|------|------|
| 无 Key 离线剧本引擎 | 已约定由你在模型层处理可用性 |
| 直连 Hive / 读原始 JSONL | 安全与口径 |
| 模型自由 SQL | 范围爆炸 |
| 等 G 步骤 7 才开工 | 冒烟可演示即可 |
| 把 smoke 当生产运营结论 | 答辩诚信 |

---

## 故障排查树

```text
chat 500 / 连不上
 ├─ 8080 没起？ → backend\start.bat
 ├─ import agent 失败？ → PYTHONPATH / sys.path
 └─ LLM 401？ → Key / Base URL / 模型名

steps 为空、答案在瞎编
 ├─ tools 没传给 LLM？
 ├─ system.md 没加载？
 ├─ 加「强制先 tool」守卫
 └─ 看厂商是否要求 tool_choice=auto/required

数字与大屏不一致
 ├─ 是否走了错误 BASE_URL？
 ├─ 是否读了旧导出？
 └─ 模型改写了数字？ → 强调 prompt；展示 steps 里原始 JSON 自证

负面率被说成非 0
 └─ 打开 steps[0] 原始 data.negative_rate；修 prompt；重跑剧本 1
```

---

## 文档关系

| 文档 | 用途 |
|------|------|
| **本文** | 按步编码、自测、勾选 |
| `阶段H_Agent开发说明书.md` | 答辩口径与范围 |
| `api_contract_v0.md` | HTTP 字段真理源 |
| `阶段G_冒烟运行手册.md` | 起 G、错误态 |

---

**开工：从 H0.1 勾选开始。卡在某一小步时，用该步的「勾选 / 自测命令」定位，不要跳过 H1 直接堆 Prompt。**
