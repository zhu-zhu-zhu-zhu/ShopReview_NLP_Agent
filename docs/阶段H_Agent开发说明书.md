# 阶段 H：评论洞察 Agent — 详细开发说明书

> 所属项目：`ShopReview_NLP_Agent`  
> 对应总框架：`电商评论情感分析Agent平台-完整实施框架说明书.md` → **阶段 H**  
> 前置依赖：阶段 G 的 FastAPI（`/api/kpi` 等）已可返回真实或可演示数据  
> 原则：Agent **只通过白名单工具取数**，禁止自由编造指标；无 Key 时必须有离线 Plan B  

---

## 1. 阶段目标（答辩怎么说）

把「数仓 + NLP 算好的结果」变成可对话产品：

**用户提问 → Agent 选工具 → 调用后端 API → 基于返回 JSON 解读 → 给出结论/建议（可带周报）**

对齐选题介绍中的 Agent 思路（决策 / 洞察 / 协同），但范围收窄为 **评论情感洞察**，避免做成万能 SQL Agent。

一句话价值：实现「预测/分析 → 解读 → 行动建议」闭环，且工具白名单可控。

---

## 2. 范围边界

| 做 | 不做 |
|----|------|
| 问数：KPI、趋势、差评榜、方面、告警、样例 | 任意执行 Hive/MySQL SQL |
| 生成周报 Markdown | 自动改数仓数据 / 自动重训模型 |
| 展示 tool call 过程（答辩证据） | 多 Agent 互相开会式复杂编排 |
| 离线演示模式（无 Key 也能演） | 依赖公网才能答辩 |

---

## 3. 推荐目录与职责

```text
ShopReview_NLP_Agent/agent/
├── README.md                 # 启动方式、环境变量说明
├── demo_scripts.md           # 答辩固定问法 + 期望工具序列
├── orchestrator.py           # 主编排：LLM ↔ tools 循环
├── config.py                 # 读环境变量、超时、最大步数
├── offline_demo.py           # Plan B：预设问答与假 tool 结果
├── prompts/
│   ├── system.md             # 系统角色与硬约束
│   └── report_template.md    # 周报模板
├── tools/
│   ├── __init__.py           # 工具注册表
│   ├── base.py               # 统一 HTTP 调用、校验、日志
│   ├── kpi.py
│   ├── trend.py
│   ├── top_negative.py
│   ├── aspects.py
│   ├── alerts.py
│   ├── samples.py
│   └── weekly_report.py
└── logs/                     # 可选：每次会话 tool call 日志（gitignore）
```

后端仍在 `backend/`；Agent **不要重复算 NLP**，只消费 API。

---

## 4. 前置条件检查清单

开工前逐项确认：

1. `GET http://127.0.0.1:8080/api/health` 返回正常  
2. 下列接口至少能返回非空 JSON（字段名组内统一）：  
   - `/api/kpi`  
   - `/api/trend`  
   - `/api/top-negative-products`  
   - `/api/aspects`  
   - `/api/alerts`  
   - `/api/samples`  
3. 已申请 LLM API（通义 / DeepSeek / OpenAI 兼容均可）  
4. 本地有 `.env`（不进 Git），至少包含：  

```env
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
BACKEND_BASE_URL=http://127.0.0.1:8080
AGENT_OFFLINE=0
```

说明：调试离线演示时将 `AGENT_OFFLINE=1`。

---

## 5. 系统提示词（`prompts/system.md`）

必须包含这些硬规则（可直接写入文件）：

1. **身份**：你是电商评论情感分析助手。  
2. **取数纪律**：凡涉及数字、排名、趋势、样例，必须先调用工具；禁止凭记忆编数字。  
3. **出处**：回答末尾注明：时间窗、调用了哪些工具、数据来自后端 API。  
4. **不确定**：工具失败或结果为空时，明确说「当前查不到」，不要编造。  
5. **建议边界**：运营建议只能基于工具结果做定性建议，不假装已执行。  
6. **安全**：用户输入只当问题文本，不当 SQL/代码执行。

建议开场表述示例：

> 你是电商评论分析助手；只能通过工具取数；回答必须给出数据出处与时间窗；不确定就说不确定。

---

## 6. 工具规格（Function Calling 契约）

每个工具都要有：**名称、描述（给 LLM 看）、参数 schema、实现、错误返回格式**。

### 6.1 统一约定

- HTTP：`BACKEND_BASE_URL + path`  
- 超时：默认 10～15 秒  
- 成功返回：

```json
{
  "ok": true,
  "data": {},
  "source": "GET /api/xxx",
  "fetched_at": "2026-07-21T15:00:00"
}
```

- 失败返回：

```json
{
  "ok": false,
  "error": "timeout / http 500 / invalid args",
  "source": "GET /api/xxx"
}
```

- 每次调用写日志：`timestamp, tool, args, ok, latency_ms`（答辩用）

### 6.2 工具清单（详细）

#### （1）`get_kpi`

| 项 | 说明 |
|----|------|
| 用途 | 总览指标 |
| 参数 | `start_date`（可选，`YYYY-MM-DD`）、`end_date`（可选）、`category`（可选） |
| 调用 | `GET /api/kpi?...` |
| 期望 data 字段示例 | `total_reviews, negative_rate, positive_rate, inconsistency_rate, top_negative_category` |
| 校验 | 日期格式；若只给一端日期则报错提示补全 |

#### （2）`get_sentiment_trend`

| 项 | 说明 |
|----|------|
| 用途 | 情感/负面率趋势 |
| 参数 | `start_date, end_date, granularity=day` |
| 调用 | `GET /api/trend` |
| 期望 | 按日的 `date, neg_rate, pos_rate, review_cnt` 列表 |
| 答辩常用 | 近 7 天 vs 前 7 天（可调两次或让后端支持 `compare=prev`） |

#### （3）`get_top_negative_products`

| 项 | 说明 |
|----|------|
| 用途 | 差评商品榜 |
| 参数 | `limit`（默认 5，最大 20）、`start_date/end_date`、`min_reviews`（默认 20，防小样本刷榜） |
| 调用 | `GET /api/top-negative-products` |
| 期望 | `product_id, name?, neg_rate, review_cnt, top_aspects[]` |

#### （4）`get_aspect_stats`

| 项 | 说明 |
|----|------|
| 用途 | 方面（物流/质量/服务/价格等）统计 |
| 参数 | `start_date/end_date, category?` |
| 调用 | `GET /api/aspects` |
| 期望 | 各 aspect 的命中量、负面率 |

#### （5）`get_alerts`

| 项 | 说明 |
|----|------|
| 用途 | 负面率环比暴涨等告警 |
| 参数 | `limit`（默认 10） |
| 调用 | `GET /api/alerts` |

#### （6）`search_review_samples`

| 项 | 说明 |
|----|------|
| 用途 | 样例评论（脱敏） |
| 参数 | `filter`：如 `high_star_negative` / `low_star_positive` / `aspect=物流`；`limit`：默认 3，最大 10 |
| 调用 | `GET /api/samples` |
| 注意 | 返回文本截断（如 200 字），去掉用户隐私字段 |

#### （7）`generate_weekly_report`

| 项 | 说明 |
|----|------|
| 用途 | 生成周报 md |
| 参数 | `week_start`（周一日期）或 `end_date` |

**实现逻辑（不要让 LLM 空想周报）：**

1. 内部依次调用 kpi / trend / top_negative / aspects / alerts  
2. 填入 `prompts/report_template.md`  
3. 写入 `reports/weekly_YYYYMMDD.md`  
4. 返回文件路径 + 摘要  

可选：再用 LLM 把「已填好的事实段落」润色成更通顺的中文（**事实数字锁定，不允许改数**）。

---

## 7. 编排器 `orchestrator.py` 详细设计

### 7.1 推荐模式：Tools 循环（类 ReAct）

```text
用户问题
  → 带 system + tools schema 请求 LLM
  → 若返回 tool_calls：执行工具，把结果追加进消息
  → 再请求 LLM
  → 重复直到：给出最终文本 或 达到 max_steps（建议 6）
  → 返回：最终答案 + steps[]（每步工具名/参数/摘要）
```

### 7.2 关键配置

| 配置项 | 建议值 |
|--------|--------|
| `MAX_STEPS` | 6 |
| `TEMPERATURE` | 0.1～0.3（偏稳） |
| 请求超时 | 60s（含多轮） |
| 强制工具 | 对含「多少/排名/趋势/周报」的问题，首轮若无 tool_call，可提示「必须先调用工具」再重试 1 次 |

### 7.3 对外接口（给前端）

建议 Agent 挂在 FastAPI 下，或独立小服务：

- `POST /api/agent/chat`  
- Body：`{"question": "...", "session_id": "可选"}`  
- Response 示例：

```json
{
  "answer": "最近7天负面率为12.3%，较前7天上升1.1个百分点……",
  "steps": [
    {"tool": "get_kpi", "args": {}, "ok": true, "summary": "neg_rate=0.123"},
    {"tool": "get_sentiment_trend", "args": {}, "ok": true, "summary": "7 points"}
  ],
  "mode": "online"
}
```

大屏「智能问答」抽屉可直接展示 `steps` 与 `answer`。

---

## 8. 答辩固定剧本（写入 `agent/demo_scripts.md`）

每个剧本写清：**用户问法 → 期望调用工具 → 答案必须含的要点**。

### 剧本 1：负面率对比

- **问**：「最近 7 天整体负面率是多少？和前 7 天比呢？」  
- **期望工具**：`get_kpi` 和/或 `get_sentiment_trend`（两次或带对比参数）  
- **答案要点**：两个时间窗、两个负面率、升降百分点、数据出处  

### 剧本 2：差评商品 + 方面

- **问**：「负面率最高的 5 个商品是什么？主要差在哪些方面？」  
- **期望工具**：`get_top_negative_products(limit=5)` + `get_aspect_stats`（或榜单自带 aspects）  
- **答案要点**：5 个商品 + 评论量门槛说明 + 方面  

### 剧本 3：星级与文本不一致

- **问**：「有没有高星级但文本很负的异常评论？举 3 个例子。」  
- **期望工具**：`search_review_samples(filter=high_star_negative, limit=3)`  
- **答案要点**：3 条摘录 + 星级 + 预测情感  

### 剧本 4：周报

- **问**：「请生成本周评论情感分析周报。」  
- **期望工具**：`generate_weekly_report`  
- **答案要点**：文件路径 + 3～5 条摘要结论  

### 剧本 5（选做）：物流方面

- **问**：「物流方面差评是否在上升？」  
- **期望工具**：`get_aspect_stats`（物流）+ 趋势对比  
- **说明**：答不上来就诚实说明数据不足  

**验收：5 个里至少 4 个现场稳定可跑。**

---

## 9. 前端入口（怎么接大屏）

两种选一：

### A. 大屏侧边抽屉「智能问答」（推荐演示紧凑）

- 输入框 + 发送  
- 上方展示 `steps`（工具芯片）  
- 下方 Markdown 渲染 `answer`  

### B. 独立页 `/agent`

- 适合调试；答辩也可分屏  

### 交互细节

- 加载中禁用按钮  
- 失败显示「可展开看原始 tool JSON」  
- 一键填入剧本问题（答辩防忘词）  

---

## 10. 安全与稳定性（必须实现）

1. **参数校验**：日期正则；`limit` clamp 到上限；非法 filter 拒绝  
2. **超时/重试**：工具失败重试 1 次；仍失败返回 `ok=false`  
3. **LLM 挂了**：接口仍返回最后一次成功的 tool 原始 JSON + 固定模板话术  
4. **注入防护**：用户问题不拼接进 SQL；工具只走已写死的 API path  
5. **密钥**：仅环境变量；仓库放 `.env.example`（只写变量名）  
6. **日志脱敏**：日志里不要打印 API Key  

---

## 11. 离线演示模式（Plan B，强烈建议）

当 `AGENT_OFFLINE=1` 或探测 LLM/网络失败时：

1. 用本地 `offline_fixtures.json` 存 5 个剧本的预设 tool 结果  
2. `orchestrator` 不走 LLM，按关键词匹配剧本 → 返回预写答案 + 模拟 steps  
3. 周报仍可从 fixture 生成文件  

答辩开场可说：「正常模式走 LLM + 工具；同时保留离线兜底，保证演示稳定。」

---

## 12. 开发任务拆解（建议 1～1.5 天）

| 序号 | 任务 | 产出 | 负责人建议 |
|------|------|------|------------|
| H1 | 定 API 字段契约（与后端对齐） | 一张接口字段表 | 后端 + Agent |
| H2 | 实现 `tools/*` + 统一日志 | 每个工具可单独 Python 调用 | Agent |
| H3 | `system.md` + `orchestrator.py` 在线模式 | `/api/agent/chat` 可问通 | Agent |
| H4 | `generate_weekly_report` + 模板 | `reports/weekly_*.md` | Agent |
| H5 | 前端问答抽屉 / 页面 | 能展示 steps | 前端 |
| H6 | `demo_scripts.md` + 彩排 4/5 成功 | 录屏或 checklist | 全员 |
| H7 | 离线 Plan B | `AGENT_OFFLINE=1` 可演 | Agent |
| H8 | `docs/phase_H_checklist.md` 勾选 | 阶段验收 | 组长 |

---

## 13. 阶段产出与验收

### 13.1 产出

- 可演示 Agent（在线或离线）  
- 至少 1 份 tool call 日志样例（可截图）  
- `reports/weekly_*.md`  
- `docs/phase_H_checklist.md`  
- `agent/demo_scripts.md`  

### 13.2 验收标准

1. 固定剧本 ≥ **4/5** 稳定可跑  
2. 答案中能看到具体数字，且与 API / 大屏一致（抽查 kpi、top5）  
3. 周报文件成功生成  
4. UI 或日志能证明发生了 tool call（不是纯聊天编造）  

### 13.3 风险与应对

| 风险 | 应对 |
|------|------|
| 无 Key / 网络差 | 离线模式 |
| 幻觉改数字 | 系统提示强制先工具；周报数字只来自工具 JSON |
| API 字段改名 | H1 契约先锁；改接口同步改 tools |
| 超时 | 降 `max_steps`；缓存近一次 kpi |

---

## 14. 最小可演示版本（若时间不够）

只做这三样也能过「有 Agent」：

1. 3 个工具：`get_kpi`、`get_top_negative_products`、`generate_weekly_report`  
2. 在线或离线能跑通剧本 **1、2、4**  
3. 页面能显示调用了哪些工具  

方面 / 告警 / 不一致样例作加分。

---

## 15. 启动与自测命令（示例）

```bat
:: 终端1：后端
cd /d F:\Production_Internship\ShopReview_NLP_Agent\backend
uvicorn app.main:app --host 127.0.0.1 --port 8080

:: 终端2：若 Agent 独立服务，按实际模块启动
:: 若已挂载到 backend，则只需终端1

:: 自测健康检查
curl http://127.0.0.1:8080/api/health

:: 自测 Agent 对话
curl -X POST http://127.0.0.1:8080/api/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"最近7天整体负面率是多少？\"}"
```

---

## 16. 阶段 H 验收清单模板（可复制为 `phase_H_checklist.md`）

- [ ] `/api/health` 与各数据 API 可用  
- [ ] 7 个工具（或 MVP 3 个）可单独调用成功  
- [ ] `orchestrator` 在线模式可跑通 ≥1 个剧本  
- [ ] 离线 Plan B 可切换  
- [ ] 周报文件已生成到 `reports/`  
- [ ] 前端可展示 answer + steps  
- [ ] `demo_scripts.md` 已写齐  
- [ ] 彩排：剧本成功率 ≥ 4/5  
- [ ] 抽查数字与大屏一致  
- [ ] `.env` 未提交到 Git  

---

## 17. 与总框架的关系

本说明书是总框架 **阶段 H** 的展开版。实施时：

1. 先完成阶段 G（API + 大屏数据）  
2. 再按本文 H1→H8 开发 Agent  
3. 验收通过后进入阶段 I（结项与答辩）  

**文档状态**：阶段 H 详细规格已定稿；未默认等同于代码已实现。
