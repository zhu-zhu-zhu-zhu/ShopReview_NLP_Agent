# 阶段 G：服务层 + 可视化大屏 — 详细开发说明书

> 所属项目：`ShopReview_NLP_Agent`  
> 对应总框架：`电商评论情感分析Agent平台-完整实施框架说明书.md` → **阶段 G**  
> 前置依赖：阶段 F 已产出下游安全导出 `exports/agent/smoke/`（大屏与 Agent 共用）  
> 后续阶段：本阶段 API + 大屏验收通过后，再进入阶段 H（Agent）  
> 文档状态：Draft v0.1（已按 Phase F smoke 导出与 Amazon Fashion 决策对齐）

---

## 0. 与仓库现状对齐（先读）

| 项 | 当前事实 |
|----|----------|
| 数仓 Phase F | 已导出安全 JSON：`exports/agent/smoke/` |
| FastAPI / 大屏 | **尚未落地**（本阶段要做） |
| production DWS / MySQL | 非本阶段硬前置；G-now 先用 smoke |
| 指标性质 | smoke 为契约/合成数据；`production_business_metrics=false` |
| 商品主键 | `parent_asin` |
| 方面词表 | 服装英文受控词（见 `docs/ASPECT_WAREHOUSE_CONTRACT.md`） |
| 推荐顺序 | **F 导出 → G 大屏+API → H Agent**（不要先做 Agent 再补大屏） |

**说明：** 目录名 `exports/agent/smoke` 来自数仓命名，实质是**下游安全指标包**，大屏与 Agent 共用，不表示「仅 Agent 可读」。

---

## 1. 阶段目标（答辩怎么说）

把数仓算好的 DWS/导出结果变成「可演示产品」：

**安全 JSON（smoke）→ FastAPI 指标服务 → 可视化大屏一屏讲清情感故事**

一句话价值：评委不需要查 Hive，也能看到 KPI、商品差评、方面与原因，并看清数据范围局限。

本阶段同时**锁定与 Agent 共用的 HTTP 契约**，阶段 H 只消费本阶段 API，不再另起一套字段。

---

## 2. 范围边界

| 做 | 不做 |
|----|------|
| 基于 smoke 的 FastAPI 指标服务 | 等 production DWS 才开始画大屏 |
| 情感洞察大屏（KPI / 占比 / Top 商品 / 方面 / 原因） | 复杂权限、多租户、实时推送 |
| 顶栏展示 `data_scope` 与非生产说明 | 静默写死假数瞒过答辩 |
| 接口字段与 smoke、阶段 H 契约对齐 | 前端直连 Hive / 读原始 JSONL |
| （可选）趋势、告警、样例接口占位 | 把 smoke 说成全站真实运营数据 |

---

## 3. 数据源策略（两阶段）

| 阶段 | Provider | 数据源 | 目标 |
|------|----------|--------|------|
| **G-now（立即）** | `SmokeJsonProvider` | `exports/agent/smoke/*.json` | 可演示 API + 大屏 |
| **G-later（有正式指标后）** | `WarehouseProvider` / MySQL | production DWS 或同步库 | 同一套路由，只换 Provider |

```text
exports/agent/smoke/
├── manifest.json              # 名片：范围、是否生产指标、文件列表
├── sentiment_overview.json    # → /api/kpi
├── product_sentiment.json     # → /api/top-negative-products
├── aspect_summary.json        # → /api/aspects
└── negative_reasons.json      # → /api/negative-reasons
```

大屏**必须经 FastAPI 取数**；允许配置 `DATA_MODE=smoke|warehouse`，但禁止前端私自造数且不标注。

---

## 4. 推荐目录与职责

```text
ShopReview_NLP_Agent/
├── backend/
│   ├── README.md
│   ├── requirements.txt
│   ├── .env.example
│   ├── start.bat                 # 或 start.ps1
│   └── app/
│       ├── main.py               # FastAPI 入口、CORS
│       ├── config.py             # DATA_MODE、SMOKE_EXPORT_DIR、端口
│       ├── providers/
│       │   ├── base.py
│       │   ├── smoke_json.py     # 读 exports/agent/smoke
│       │   └── warehouse.py      # G-later 占位
│       ├── schemas/              # 响应模型（与契约一致）
│       └── routers/
│           ├── health.py
│           ├── kpi.py
│           ├── products.py
│           ├── aspects.py
│           └── negative_reasons.py
├── dashboard/
│   ├── README.md
│   ├── start.bat
│   └── ...                       # React/Vue 等；优先复用既有大屏壳
└── docs/
    ├── 阶段G_服务层与大屏开发说明书.md   # 本文
    └── api_contract_v0.md              # 建议：接口字段表（供 H 复用）
```

职责边界：

- **数仓**：产出并校验导出；不维护大屏 UI  
- **服务层（本阶段）**：Provider + 路由 + 健康检查与 `data_scope` 元信息  
- **前端（本阶段）**：可视化与文案；不直连 Hive  
- **Agent（阶段 H）**：只调本阶段 HTTP（或离线兜底），不重算指标  

---

## 5. 前置条件检查清单（G-now）

1. 可读：`exports/agent/smoke/manifest.json` 及四个数据集 JSON  
2. `production_business_metrics === false`（UI 必须体现）  
3. 本机可跑 Python 3 + 拟用前端环境  
4. 端口约定：后端 `8080`，前端 `5173`（或组内统一）  
5. `.env` 示例：

```env
DATA_MODE=smoke
SMOKE_EXPORT_DIR=exports/agent/smoke
API_HOST=127.0.0.1
API_PORT=8080
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

---

## 6. API 契约（与大屏 / Agent 共用）

### 6.1 统一约定

- Base URL：`http://127.0.0.1:8080`  
- JSON UTF-8  
- 成功时尽量带：`data_scope`、`schema_version`、`source`（如 `smoke:sentiment_overview.json`）  
- smoke 下无数据的能力：返回 **明确未实现**（如 HTTP 501 或 `{"ok":false,"error":"not_available_in_smoke"}`），禁止静默空成功装成「全 0 真实业务」

### 6.2 G-now 必做接口

#### （1）`GET /api/health`

```json
{
  "ok": true,
  "data_mode": "smoke",
  "schema_version": "draft_v0.1",
  "production_business_metrics": false,
  "data_scope_summary": "phase_d_e_smoke_contract + synthetic_aspect_contract_smoke",
  "export_name": "Phase F warehouse smoke"
}
```

字段可从 `manifest.json` 映射。

#### （2）`GET /api/kpi`

| 项 | 说明 |
|----|------|
| 来源 | `sentiment_overview.json` → `records[0]` |
| 核心字段 | `review_count`、`user_count`、`product_count`、正/中/负 count 与 rate、`average_rating`、`data_scope` |
| 注意 | smoke **无** `inconsistency_rate`；勿编造 |
| 可选查询参数 | G-now 可忽略日期；若传入日期且无趋势数据，返回说明「当前为快照、不支持时间窗过滤」 |

#### （3）`GET /api/top-negative-products`

| 项 | 说明 |
|----|------|
| 来源 | `product_sentiment.json` |
| 排序 | `negative_rate`↓，再 `negative_count`↓，再 `review_count`↓ |
| 参数 | `limit`（默认 10，最大 50）；`min_reviews`（**smoke 默认 1**；正式数据建议 ≥20） |
| 返回字段 | `parent_asin`、`product_title`、`store_name`、计数与比率、`data_scope` |

#### （4）`GET /api/aspects`

| 项 | 说明 |
|----|------|
| 来源 | `aspect_summary.json` |
| 参数 | 可选 `aspect=` 过滤（`size`/`delivery`/…） |
| 返回 | `aspect`、`reason_code`、`reason_name`、`mention_count`、情感计数与 `negative_rate`、`average_confidence`、`extractor_version`、`data_scope` |
| 展示 | 前端提供中英对照标签 |

#### （5）`GET /api/negative-reasons`

| 项 | 说明 |
|----|------|
| 来源 | `negative_reasons.json` |
| 参数 | `limit`；可选 `parent_asin` |
| 返回 | 商品 × 方面 × 原因及 `reason_share` |

### 6.3 G-now 暂缓接口（占位即可）

| 接口 | 状态 | 说明 |
|------|------|------|
| `GET /api/trend` | ⏸ | 无日序列；返回未实现 |
| `GET /api/alerts` | ⏸ | 无告警快照 |
| `GET /api/samples` | ⏸ | 安全导出故意无全文；待脱敏样例后再做 |

### 6.4 响应包装建议（可选但推荐）

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "data_mode": "smoke",
    "schema_version": "draft_v0.1",
    "data_scope": "phase_d_e_smoke_contract",
    "production_business_metrics": false,
    "source": "smoke:sentiment_overview.json"
  }
}
```

锁契约后写入 `docs/api_contract_v0.md`，阶段 H 直接引用。

---

## 7. 大屏面板设计（按 smoke 能力）

### 7.1 一屏故事（推荐布局）

| 区域 | 内容 | 数据接口 |
|------|------|----------|
| 顶栏 | 项目名「评论情感洞察」+ **数据模式角标**（Smoke / 非生产业务指标）+ `data_scope` 摘要 | `/api/health` |
| KPI 条 | 评论量、正面率、中性率、负面率、均分 | `/api/kpi` |
| 中央 | **正/中/负占比快照**（饼图或堆叠条）；**不要**强行画「近 7 日趋势」 | `/api/kpi` |
| 左 | 方面负面提及（按 `aspect` 聚合或展示 reason 列表） | `/api/aspects` |
| 右 | 差评商品 TOP（`parent_asin`+标题截断+负面率） | `/api/top-negative-products` |
| 右下或底左 | 差评原因 TOP | `/api/negative-reasons` |
| 底栏 | 数据源说明、manifest 导出名、`production_business_metrics=false` | `/api/health` |

### 7.2 明确不做或占位的面板

- 日/周情感趋势折线 → 无数据则显示「当前导出为快照，暂无时间序列」  
- 告警跑马灯 → 占位或隐藏  
- 差评原文滚动 → 不做（隐私与导出策略）  

### 7.3 文案与交互

- 方面：`size`→尺码，`delivery`→物流相关，`material`→材质，等  
- Top 商品：smoke 下标注「小样本可能 review_count=1」  
- 加载失败：明确错误，禁止回退到无标注假数  
- 可选：一键「刷新」重新拉 API  

### 7.4 前端技术建议

- 优先复用 DataCanvasLab / EcommerceDW-Dashboard 壳，改主题与接口  
- 图表：ECharts 等即可  
- 开发代理：`5173` → `8080`，注意 CORS  

---

## 8. 后端实现要点

1. **Provider 模式**：路由不直接 `open(json)` 散落；统一 `get_provider()`  
2. **启动校验**：`DATA_MODE=smoke` 时检查 manifest 与文件存在，否则 `/api/health` 报错  
3. **只读**：不写回数仓、不改 exports  
4. **日志**：记录 path、耗时；不打密钥  
5. **CORS**：放开前端源  
6. **G-later**：新增 Provider 后，路由与 schema 尽量不动  

---

## 9. 开发任务拆解

| 序号 | 任务 | 产出 | 依赖 |
|------|------|------|------|
| G0 | 读通 smoke 四文件 + manifest 字段映射表 | `docs/api_contract_v0.md` 草稿 | F 导出 |
| G1 | `SmokeJsonProvider` + `/api/health` | 健康检查含局限字段 | G0 |
| G2 | 实现 kpi / top-negative / aspects / negative-reasons | curl 可测 | G1 |
| G3 | 大屏壳 + 顶栏局限角标 + KPI + 占比图 | 首屏可演示 | G2 |
| G4 | Top 商品 + 方面 + 差评原因面板 | 一屏故事完整 | G3 |
| G5 | 错误态、空态、501 占位（trend/alerts/samples） | 答辩不翻车 | G2 |
| G6 | `start.bat` / README + 截图录屏 | 一键启动 | G4 |
| G7 | （可选）WarehouseProvider 骨架 | 为正式指标预留 | G2 |
| G8 | `docs/phase_G_checklist.md` 勾选 | 阶段验收 | 全员 |

**完成 G2～G4 且 checklist 通过后，再启动阶段 H。**

---

## 10. 启动与自测（示例）

```bat
:: 终端1：后端
cd /d F:\Production_Internship\ShopReview_NLP_Agent\backend
uvicorn app.main:app --host 127.0.0.1 --port 8080

:: 健康检查
curl http://127.0.0.1:8080/api/health

:: KPI
curl http://127.0.0.1:8080/api/kpi

:: Top 商品
curl "http://127.0.0.1:8080/api/top-negative-products?limit=5&min_reviews=1"

:: 终端2：前端（按实际项目）
cd /d F:\Production_Internship\ShopReview_NLP_Agent\dashboard
npm run dev
```

对账抽查：大屏 KPI 数字 = `sentiment_overview.json` 中对应字段（允许展示层百分比格式化，但原始比率一致）。

---

## 11. 阶段产出与验收

### 11.1 产出

- 可访问 FastAPI（G-now smoke）  
- 可演示大屏  
- `docs/api_contract_v0.md`（或等价接口表）  
- `docs/phase_G_checklist.md`  
- 大屏截图 / 30～60 秒录屏  
- 一键启动说明  

### 11.2 验收标准

1. `/api/health` 正常，且暴露 `data_mode`、`production_business_metrics`  
2. 四个核心接口返回与 smoke JSON 一致（抽查 kpi、top5、aspects、reasons）  
3. 大屏一屏能讲完：总量与三率 → 占比 → Top 商品 → 方面/原因  
4. 顶栏/底栏有非生产 / `data_scope` 说明  
5. 无后端时有明确错误提示（不静默假数）  
6. 趋势/告警/样例未实现时不伪装成真实能力  

### 11.3 风险与应对

| 风险 | 应对 |
|------|------|
| 等正式 DWS 才开工 | G-now 先用 smoke |
| 前端写死数字 | 强制走 API；答辩改 limit 验证 |
| 字段与 Agent 两套 | G0 先锁契约，H 复用 |
| 小样本刷榜 | `min_reviews` 可配 + UI 说明 |
| 把烟测当生产 | 角标 + health 字段强制展示 |

---

## 12. 最小可演示版本（若时间不够）

1. 后端：health + kpi + top-negative-products + aspects  
2. 大屏：顶栏局限说明 + KPI + 占比 + Top5 + 方面条形图  
3. 一张全屏截图进结项报告  

`negative-reasons` 与精致动效可后补；趋势/告警/样例不阻塞 G 验收。

---

## 13. 阶段 G 验收清单模板（可复制为 `phase_G_checklist.md`）

- [ ] `exports/agent/smoke/manifest.json` 可读  
- [ ] `SmokeJsonProvider` 启动校验通过  
- [ ] `/api/health` 含 `data_mode` 与 `production_business_metrics`  
- [ ] `/api/kpi` 与 overview JSON 对账通过  
- [ ] `/api/top-negative-products` 对账通过（`parent_asin`）  
- [ ] `/api/aspects` 对账通过  
- [ ] `/api/negative-reasons` 对账通过（或 MVP 声明暂缓但 checklist 注明）  
- [ ] 大屏顶栏有 Smoke / 非生产说明  
- [ ] 中央为占比快照（非假趋势）  
- [ ] 断后端时有明确错误提示  
- [ ] `docs/api_contract_v0.md` 已写，可供阶段 H 使用  
- [ ] 截图/录屏已归档  
- [ ] 一键启动文档可用  

---

## 14. 与总框架 / 阶段 H 的关系

```text
阶段 F：DWS + exports/agent/smoke
    → 阶段 G（本文）：FastAPI + 大屏（G-now 读 smoke）
    → 阶段 H：Agent 调同一套 /api/*（详见 docs/阶段H_Agent开发说明书.md）
```

1. **不要**在 G 未完成时把 Agent 当主路径优先开发  
2. G 锁好的 API 契约，是 H 的前置交付物之一  
3. G-later 换正式指标时，保持路由稳定，Agent 与大屏同时受益  

相关文档：

- `docs/PHASE_F_DWS_SMOKE_REPORT.md`  
- `docs/ASPECT_WAREHOUSE_CONTRACT.md`  
- `exports/agent/smoke/manifest.json`  
- `docs/阶段H_Agent开发说明书.md`  

**文档状态**：阶段 G 详细规格 Draft v0.1；未默认等同于 `backend/` / `dashboard/` 代码已实现。

动手做冒烟时，请按可勾选手册执行：

**[阶段G_冒烟测试执行步骤.md](./阶段G_冒烟测试执行步骤.md)**
