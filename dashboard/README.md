# ShopReview 情感作战室

基于 React、TypeScript、Vite 和 ECharts 的 production serving v2 数据大屏。前端只访问 FastAPI，不包含 mock 业务数据，也不直接读取 Hive、MySQL、JSONL 或本地导出。

## 启动

```powershell
# 窗口 1：仓库根目录
.\backend\start_warehouse.bat

# 窗口 2
cd dashboard
.\node_modules\.bin\vite.cmd --host 127.0.0.1
```

打开 `http://127.0.0.1:5173`。默认 API 地址由 `VITE_API_BASE=http://127.0.0.1:8080` 控制。

## 页面区域

- 生产状态栏：后端、批次、模型和 warehouse 模式；
- KPI：健康指数、评论量、正/中/负比例、平均评分、告警；
- 情感时间河：月度全景与近 365 日趋势；
- 风险热力榜：店铺/商品差评榜与好评榜切换；
- 告警雷达：按 CRITICAL、HIGH、MEDIUM、LOW 展示；
- 星级 × 预测矩阵与预测置信度；
- 规则方面与全局负面原因；
- 认证购买对比和脱敏评论样例；
- ReviewOps Copilot AI 风险调查抽屉。

## 动效和无障碍

- 页面分区按顺序淡入，不改变布局尺寸；
- KPI 仅在值变化时滚动；
- ECharts 使用平滑首次绘制与切换动画；
- 排行榜使用与情感方向一致的颜色：好评青绿色、差评洋红色；
- Agent 启动器可拖动，抽屉打开时启动器隐藏；
- 支持 `prefers-reduced-motion: reduce`，关闭数字滚动、扫描、呼吸和流光，仅保留简单淡入。

## 生产构建

```powershell
cd D:\bdt-app-course\projects\ShopReview_NLP_Agent\dashboard
npm.cmd run build
```

构建输出 `dashboard/dist/`，属于本地生成物，不应提交。当前 build PASS；Vite 仅提示主包超过 500 kB，不影响构建结果。

## 故障判断

- 页面提示后端不可用：检查 `http://127.0.0.1:8080/docs`；
- API 正常但无数据：检查 `/api/health` 的批次、模型和表行数；
- PowerShell 阻止 `npm.ps1`：使用 `npm.cmd` 或 `vite.cmd`；
- Agent 无法回答：先确认普通 warehouse API 正常，再检查本地 `agent/.env` Key。
