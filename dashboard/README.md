# ShopReview 评论情感洞察大屏（阶段 G 冒烟）

Vite + React + ECharts。所有指标只经 FastAPI，**禁止**直接 import `exports/agent/smoke` JSON。

完整复现：`docs/阶段G_冒烟运行手册.md`。

## 启动顺序（必须）

1. 先启动后端：`..\backend\start.bat` → http://127.0.0.1:8080  
2. 再启动本大屏：`start.bat` → http://127.0.0.1:5173  
3. 浏览器打开大屏；F12 → Network 确认请求打到 **8080**

Windows 请用 `npm.cmd`（避免 PowerShell 执行策略拦 `npm.ps1`）。

## 首次安装

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent\dashboard
copy .env.example .env
npm.cmd install
start.bat
```

## 配置

`dashboard/.env`：

```env
VITE_API_BASE=http://127.0.0.1:8080
```

## 当前大屏

唯一入口：**情感作战室（Command Wall）** — 深色监控投屏布局。

打开 http://127.0.0.1:5173（需先启 warehouse API）。

## 面板与接口

| 区域 | API |
|------|-----|
| 顶栏 / 底栏 | `/api/health` |
| KPI / 占比 | `/api/kpi` |
| 方面 | `/api/aspects` |
| Top 商品 | `/api/top-negative-products` |
| 差评原因 | `/api/negative-reasons` |
| 能力条 | `/api/trend` `/api/alerts` `/api/samples` → 期望 501「暂未接入」 |
| **智能问答抽屉** | `POST /api/agent/chat`（DeepSeek + 白名单工具） |

## 智能问答（阶段 H）

1. 顶栏点 **智能问答** 打开侧抽屉  
2. 可用剧本芯片一键提问，或自行输入后 Enter 发送  
3. 展示 `steps`（tool 芯片）与 `answer`；可展开原始 JSON  

需后端已挂载 `/api/agent/chat` 且配置了 `agent/.env` 中的 `LLM_API_KEY`。

## 错误态（步骤 6）

| 场景 | 期望 |
|------|------|
| 关掉后端后点「刷新」 | 红色「后端不可用」提示，不展示假 KPI |
| 后端开着，trend/alerts/samples | 能力条显示「暂未接入」，不画假趋势 |

## 冒烟说明

顶栏 **Smoke / 非生产业务指标**。数字来自契约导出，不能当作全站运营结论。

正式版：后端切 `DATA_MODE=warehouse` 后，本大屏通常无需改接口路径。
