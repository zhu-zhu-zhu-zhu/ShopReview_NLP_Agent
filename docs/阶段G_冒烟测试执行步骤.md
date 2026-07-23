# 阶段 G 冒烟测试 — 详细执行步骤

> 目标：用 `exports/agent/smoke` 跑通 **FastAPI → 可视化大屏**，不接 Hive、不等 NLP。  
> 依据：`docs/阶段G_服务层与大屏开发说明书.md`  
> 完成后：勾选文末清单，再进入阶段 H（Agent）。  
> 预留：`DATA_MODE=warehouse` 与 `WarehouseProvider` 空壳，正式 DWS 就绪后只换 Provider。

---

## 你要达成的冒烟结果（一句话）

浏览器打开大屏 → 数字来自 `http://127.0.0.1:8080/api/*` → 与 `exports/agent/smoke/*.json` 对得上 → 顶栏写明 **Smoke / 非生产业务指标**。

---

## 总览：8 个步骤

| 步骤 | 名称 | 预计 | 完成标志 |
|------|------|------|----------|
| 0 | 环境与数据确认 | 15 min | 5 个 JSON 能打开，分支就绪 |
| 1 | 锁 API 契约草稿 | 30 min | `docs/api_contract_v0.md` 有字段表 |
| 2 | 搭 backend 骨架 + Provider | 1～2 h | 目录齐，`smoke` 能读文件 |
| 3 | 实现 5 个核心接口 | 1～2 h | curl 全部 PASS |
| 4 | 占位 3 个暂缓接口 | 20 min | trend/alerts/samples 明确未实现 |
| 5 | 大屏最小版接 API | 2～4 h | 一屏能讲完故事 |
| 6 | 错误态与启动脚本 | 30～60 min | 断后端有提示；一键启动 |
| 7 | 对账、截图、验收勾选 | 30 min | checklist 全过；可 push |

建议分支：`agent-dev` 或 `web-front-dev`（组内约定；服务层+大屏可先放你负责的分支）。

---

## 步骤 0：环境与数据确认

### 0.1 确认 smoke 文件存在

在项目根目录检查：

```text
exports/agent/smoke/manifest.json
exports/agent/smoke/sentiment_overview.json
exports/agent/smoke/product_sentiment.json
exports/agent/smoke/aspect_summary.json
exports/agent/smoke/negative_reasons.json
```

打开 `manifest.json`，确认：

- [ ] `production_business_metrics` 为 `false`
- [ ] `files` 列表包含上述四个数据集文件

### 0.2 记下冒烟对账用的「标准答案」（KPI）

来自 `sentiment_overview.json` → `records[0]`（当前仓库值）：

| 字段 | 期望值（对账用） |
|------|------------------|
| `review_count` | `50` |
| `positive_count` | `44` |
| `neutral_count` | `6` |
| `negative_count` | `0` |
| `positive_rate` | `0.88` |
| `neutral_rate` | `0.12` |
| `negative_rate` | `0.0` |
| `average_rating` | `4.46` |
| `data_scope` | `phase_d_e_smoke_contract` |

若队友更新了导出，以**你本机 JSON 实际值**为准，改此表后再对账。

### 0.3 本机环境

- [ ] Python 3.10+（建议）
- [ ] 能创建 venv / 安装 `fastapi`、`uvicorn`
- [ ] 前端：Node.js（若用 Vite/React）；或先用纯 HTML + ECharts 最小页也行
- [ ] 端口空闲：`8080`（API）、`5173`（前端，可选）

### 0.4 Git

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
git fetch origin
git checkout agent-dev
git pull --ff-only origin agent-dev
git merge origin/main
```

（若分支策略不同，改成你们实际分支；务必带上最新的 `exports/agent/smoke`。）

**步骤 0 完成标志：** 数据在、环境在、分支在。

---

## 步骤 1：锁 API 契约（先写文档再写代码）

新建 `docs/api_contract_v0.md`，至少包含下表（复制后按实现微调）：

### 1.1 接口清单

| Method | Path | smoke 来源 | 冒烟必做 |
|--------|------|------------|----------|
| GET | `/api/health` | `manifest.json` | ✅ |
| GET | `/api/kpi` | `sentiment_overview.json` | ✅ |
| GET | `/api/top-negative-products` | `product_sentiment.json` | ✅ |
| GET | `/api/aspects` | `aspect_summary.json` | ✅ |
| GET | `/api/negative-reasons` | `negative_reasons.json` | ✅ |
| GET | `/api/trend` | 无 | ⏸ 501 / not_available |
| GET | `/api/alerts` | 无 | ⏸ |
| GET | `/api/samples` | 无 | ⏸ |

### 1.2 统一响应建议

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "data_mode": "smoke",
    "schema_version": "draft_v0.1",
    "data_scope": "...",
    "production_business_metrics": false,
    "source": "smoke:sentiment_overview.json"
  }
}
```

### 1.3 查询参数约定

| 接口 | 参数 | smoke 默认 |
|------|------|------------|
| top-negative-products | `limit`（1～50，默认 10） | — |
| top-negative-products | `min_reviews`（默认 **1**） | 正式以后改 20 |
| aspects | `aspect` 可选 | 如 `size` |
| negative-reasons | `limit`；`parent_asin` 可选 | — |

### 1.4 主键与禁忌

- 商品主键用 `parent_asin`，不要编 `product_id`
- 不要编造 `inconsistency_rate`（smoke 没有）
- 不要返回 `user_id`、完整长评原文

**步骤 1 完成标志：** `docs/api_contract_v0.md` 已定稿；后面路由按此实现。

> 契约正文见：[api_contract_v0.md](./api_contract_v0.md)

---

## 步骤 2：搭建 backend 骨架（含预留）

### 2.1 创建目录

```text
backend/
├── README.md
├── requirements.txt
├── .env.example
├── start.bat
└── app/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── providers/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── smoke_json.py
    │   └── warehouse.py      ← 预留：方法里 raise NotImplementedError
    ├── schemas/
    │   └── common.py         ← 可选：统一 Ok/Meta 模型
    └── routers/
        ├── __init__.py
        ├── health.py
        ├── kpi.py
        ├── products.py
        ├── aspects.py
        └── negative_reasons.py
```

### 2.2 `requirements.txt` 最小依赖

```text
fastapi
uvicorn[standard]
pydantic
python-dotenv
```

### 2.3 `.env.example`

```env
DATA_MODE=smoke
SMOKE_EXPORT_DIR=exports/agent/smoke
API_HOST=127.0.0.1
API_PORT=8080
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

注意：`SMOKE_EXPORT_DIR` 建议相对**仓库根目录**，启动时把 cwd 设到仓库根，或在 `config.py` 里用 `Path(__file__).resolve().parents[2]` 定位根目录。

### 2.4 Provider 抽象（预留完整版的关键）

在 `base.py` 定义接口（示例方法名，可微调但确定后不要乱改）：

- `get_health_meta() -> dict`
- `get_kpi() -> dict`
- `get_top_negative_products(limit, min_reviews) -> list`
- `get_aspects(aspect: str | None) -> list`
- `get_negative_reasons(limit, parent_asin: str | None) -> list`

`smoke_json.py`：读 JSON 实现。  
`warehouse.py`：每个方法 `raise NotImplementedError("G-later: wire to production DWS")`。

`config.py` / `get_provider()`：

```text
DATA_MODE=smoke     → SmokeJsonProvider
DATA_MODE=warehouse → WarehouseProvider
```

路由**只调用** `get_provider()`，禁止在 router 里直接 `open("exports/...")`。

### 2.5 FastAPI 入口

`main.py`：

- 创建 app
- 配置 CORS（允许 5173）
- `include_router` 挂上各路由
- 可选：启动时若 `DATA_MODE=smoke`，检查 5 个文件是否存在，缺失则日志报错

### 2.6 本地安装与空启动

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```

**步骤 2 完成标志：** 目录齐；`warehouse.py` 占位存在；能 `import app.main` 不报错。

> 本地已落地：`backend/` 骨架 + `SmokeJsonProvider` 可读 smoke 五文件 + 五路由已挂载（curl 验收见步骤 3）。

---

## 步骤 3：实现 5 个核心接口（curl 验收）

每实现一个接口，立刻 curl，不要攒到最后。

### 3.1 `GET /api/health`

从 `manifest.json` 映射：

- `ok: true`
- `data_mode: "smoke"`
- `schema_version`
- `production_business_metrics`
- `export_name`
- `data_scope_summary`（可用 sentiment + aspect 两个 scope 拼一句）

验收：

```bat
curl http://127.0.0.1:8080/api/health
```

- [ ] 返回含 `production_business_metrics: false`
- [ ] 返回含 `data_mode: smoke`

### 3.2 `GET /api/kpi`

读 `sentiment_overview.json` 的 `records[0]`，放入 `data`；`meta.source = "smoke:sentiment_overview.json"`。

```bat
curl http://127.0.0.1:8080/api/kpi
```

- [ ] `review_count` 等与步骤 0.2 表一致

### 3.3 `GET /api/top-negative-products`

- 读全部 `product_sentiment` records
- 过滤 `review_count >= min_reviews`
- 排序：`negative_rate` ↓，`negative_count` ↓，`review_count` ↓
- 截断 `limit`

```bat
curl "http://127.0.0.1:8080/api/top-negative-products?limit=5&min_reviews=1"
```

- [ ] 每条有 `parent_asin`、`product_title`、`negative_rate`
- [ ] 改 `limit=2` 只返回 2 条（证明不是前端写死）

### 3.4 `GET /api/aspects`

```bat
curl http://127.0.0.1:8080/api/aspects
curl "http://127.0.0.1:8080/api/aspects?aspect=size"
```

- [ ] 有 `aspect`、`reason_name`、`mention_count`、`negative_rate`
- [ ] `aspect=size` 时只含 size

### 3.5 `GET /api/negative-reasons`

```bat
curl "http://127.0.0.1:8080/api/negative-reasons?limit=5"
```

- [ ] 有 `parent_asin`、`reason_name`、`reason_share`

### 3.6 启动命令（开发时）

在仓库根目录（保证相对路径正确）：

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
.venv\Scripts\activate
set DATA_MODE=smoke
set SMOKE_EXPORT_DIR=exports/agent/smoke
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
```

或写进 `backend/start.bat`，内部 `cd` 到仓库根再启动。

**步骤 3 完成标志：** 5 个接口 curl 全绿；KPI 与 JSON 对账通过。

> 2026-07-22 本地验收：`/api/health`、`/api/kpi`、`/api/top-negative-products`、`/api/aspects`、`/api/negative-reasons` 全部 PASS（含 KPI 对账与 `limit=2` / `aspect=size` 过滤）。

---

## 步骤 4：暂缓接口占位（预留完整版）

实现三个路由，统一返回例如：

```json
{
  "ok": false,
  "error": "not_available_in_smoke",
  "message": "当前为 smoke 快照，无日趋势/告警/样例数据"
}
```

HTTP 可用 `501` 或 `200 + ok:false`（组内选一种写进契约，前后端一致即可）。

```bat
curl http://127.0.0.1:8080/api/trend
curl http://127.0.0.1:8080/api/alerts
curl http://127.0.0.1:8080/api/samples
```

- [ ] 不会返回「假的全 0 成功业务数据」

**步骤 4 完成标志：** 三个占位可调用且语义诚实。

> 2026-07-22 本地验收：`GET /api/trend|alerts|samples` 均返回 **501** + `error=not_available_in_smoke`，未伪装成功业务数据。

---

## 步骤 5：大屏冒烟版（接 API，不接 JSON 文件）

### 5.1 技术选型（二选一）

| 方案 | 适合 | 说明 |
|------|------|------|
| A. 新建 `dashboard/`（Vite + React/Vue + ECharts） | 从零、可控 | 推荐冒烟 |
| B. 复用已有大屏壳 | 已有 DataCanvasLab 等 | 只改 API 与文案 |

冒烟不要求视觉完美，要求**数据真、故事清**。

### 5.2 页面布局（按说明书一屏）

| 区域 | 调什么 | 显示什么 |
|------|--------|----------|
| 顶栏 | `/api/health` | 「评论情感洞察」+ 角标 `Smoke` + `非生产业务指标` + scope 摘要 |
| KPI 条 | `/api/kpi` | 评论量、正/中/负率、均分 |
| 中央 | `/api/kpi` | 正中负**占比图**（饼或条），禁止画假「近 7 日折线」 |
| 左 | `/api/aspects` | 方面/原因条形图；英文词旁注中文（size→尺码 等） |
| 右 | `/api/top-negative-products?limit=10&min_reviews=1` | Top 商品；注明小样本 |
| 底左/右下 | `/api/negative-reasons?limit=10` | 差评原因 |
| 底栏 | `/api/health` | export_name、`production_business_metrics=false` |

### 5.3 前端硬规则

- [ ] 所有数字只来自 `fetch('http://127.0.0.1:8080/api/...')`
- [ ] 禁止 `import` 本地 smoke JSON 当展示数据
- [ ] `fetch` 失败：页面显示错误文案，**不要**用假数顶上
- [ ] 配置 `VITE_API_BASE=http://127.0.0.1:8080`（或写死冒烟地址并在 README 说明）

### 5.4 方面中英对照（展示用）

`size` 尺码 · `color` 颜色 · `material` 材质 · `comfort` 舒适度 · `workmanship` 做工 · `description_mismatch` 描述不符 · `packaging` 包装 · `delivery` 物流相关 · `price` 价格 · `other` 其他

### 5.5 联调顺序

1. 先开后端（步骤 3）
2. 再开前端
3. 浏览器 F12 → Network：确认请求打到 `8080`，状态 200
4. 改后端临时把某字段改名 → 大屏应报错或空，证明没写死

**步骤 5 完成标志：** 一屏能口头讲完「总量→占比→差评商品→方面/原因」，且角标可见。

> 2026-07-22 已落地方案 A：`dashboard/`（Vite + React + ECharts）。启动顺序：`backend\start.bat` → `dashboard\start.bat` → 打开 http://127.0.0.1:5173。所有数字仅 `fetch` API，顶栏含 Smoke / 非生产角标。

---

## 步骤 6：错误态、启动脚本、README

> **2026-07-22 PASS**：能力条显示 trend/alerts/samples「暂未接入」；断后端刷新出现「后端不可用」红条；`backend/start.bat`、`dashboard/start.bat`、`start_smoke_demo.bat` 与 `docs/阶段G_冒烟运行手册.md` 已就绪。

### 6.1 错误态自测

1. 关掉后端，刷新大屏  
   - [x] 出现明确「后端不可用」类提示  
2. 后端开着，访问 `/api/trend`  
   - [x] 前端若调用则显示「暂未接入」，不假装有趋势  

### 6.2 `backend/start.bat`（示例逻辑）

- [x] 激活 venv（若有）
- [x] 设置 `DATA_MODE=smoke`
- [x] 从仓库根启动 uvicorn `:8080`

### 6.3 `dashboard/start.bat`

- [x] `npm install`（首次）
- [x] `npm run dev` → `5173`

### 6.4 `backend/README.md` / `dashboard/README.md`

写清：

- [x] 启动顺序：先 backend 后 dashboard  
- [x] 端口  
- [x] `DATA_MODE` 含义  
- [x] 冒烟数据不是生产指标  
- [x] 正式版：实现 `WarehouseProvider`，改 `DATA_MODE=warehouse`，路由不变  

**步骤 6 完成标志：** 别人按 README / [阶段G_冒烟运行手册](./阶段G_冒烟运行手册.md) 能在你电脑上复现冒烟演示。 ✅

---

## 步骤 7：最终验收、截图、提交

### 7.1 对账表（必做）

| 检查项 | 方法 | PASS？ |
|--------|------|--------|
| health 局限字段 | curl `/api/health` | ☐ |
| KPI = overview JSON | curl vs 步骤 0.2 | ☐ |
| Top 商品含 parent_asin | curl `limit=5` | ☐ |
| aspects 可过滤 | `?aspect=size` | ☐ |
| negative-reasons 有数据 | curl | ☐ |
| 大屏 KPI 与 curl 一致 | 肉眼/截图 | ☐ |
| 顶栏 Smoke 角标 | 截图 | ☐ |
| 中央是占比不是假趋势 | 截图 | ☐ |
| 断后端有错误提示 | 实测 | ☐ |
| warehouse.py 占位存在 | 看代码 | ☐ |

### 7.2 材料归档

- [ ] 大屏全屏截图 → 可放 `reports/dashboard_smoke_*.png`（若太大可只本地保留）
- [ ] （可选）30～60 秒录屏
- [ ] `docs/phase_G_checklist.md`：从说明书 §13 复制并勾选
- [ ] `docs/api_contract_v0.md` 已与实现一致

### 7.3 Git 提交建议（你本地执行）

```bat
git status
git add backend dashboard docs/api_contract_v0.md docs/phase_G_checklist.md docs/阶段G_冒烟测试执行步骤.md
git commit -m "feat(stage-g): add smoke FastAPI and dashboard for agent exports"
git push -u origin HEAD
```

发给队友：

- 分支名  
- commit hash  
- 启动命令与端口 `8080` / `5173`  
- 四个业务接口路径  

**步骤 7 完成标志：** 冒烟 G 阶段可宣布 PASS；下一步才做 Agent。

---

## 冒烟阶段明确不做（避免范围膨胀）

- 不接 Hive / 不跑生产 DWS  
- 不等 NLP 预测文件  
- 不做完整 Agent / LLM  
- 不画无数据的日趋势当真能力  
- 不把 smoke 说成全站真实运营数据  

---

## 正式版切换预留（现在埋好即可）

| 现在 | 以后队友 DWS 正式后 |
|------|---------------------|
| `SmokeJsonProvider` | 实现 `WarehouseProvider`（读 Hive/正式导出/MySQL） |
| `DATA_MODE=smoke` | `DATA_MODE=warehouse` |
| `production_business_metrics=false` | 改为 `true`（仅当确实是生产指标） |
| 同一套 `/api/*` | **路径与字段尽量不变** |
| 大屏 / 未来 Agent | 不用改工具名，只换数据 |

---

## 卡关时怎么查

| 现象 | 排查 |
|------|------|
| 404 | 路由前缀是否 `/api`；uvicorn `--app-dir` 是否正确 |
| 读不到 JSON | cwd 是否仓库根；`SMOKE_EXPORT_DIR` 路径 |
| CORS 报错 | `CORS_ORIGINS` 是否含前端源 |
| 大屏有数但和 JSON 不符 | 是否前端写死；是否看错 records |
| Top 全空 | `min_reviews` 是否误设为 20（smoke 应用 1） |

---

## 与阶段 H 的衔接

G 冒烟 PASS 之后再做 Agent：

1. Agent 工具只调本阶段已验收的 `/api/*`  
2. 先做无 LLM 的脚本冒烟（调 API 打印数字）  
3. 再接 LLM / 离线 Plan B  

详见：`docs/阶段H_Agent开发说明书.md`。
