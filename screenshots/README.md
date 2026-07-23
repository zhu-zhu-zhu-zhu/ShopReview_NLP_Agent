# 可视化大屏截图

本目录保存 ShopReview 生产数据可视化大屏的自动化截图。截图使用
`prod_v1_100k` 批次和 `tfidf_logreg_oof_v1` 模型对应的真实 warehouse API
数据，不使用 mock 数据。

## 自动生成

PowerShell 窗口 1 启动后端：

```powershell
.\backend\start_warehouse.bat
```

PowerShell 窗口 2 启动前端：

```powershell
cd .\dashboard
.\node_modules\.bin\vite.cmd --host 127.0.0.1
```

PowerShell 窗口 3 在项目根目录执行：

```powershell
.\scripts\capture_dashboard_screenshots.ps1
```

脚本复用本机 Chrome 或 Edge，不下载浏览器。也可以用环境变量
`CHROME_PATH` 指定 Chromium 浏览器可执行文件。

## 截图内容

生成结果位于 `screenshots/dashboard/`：

1. `01-dashboard-overview.png`：大屏总览、KPI、差评榜和近 365 日趋势。
2. `02-positive-rankings.png`：店铺好评榜和商品好评榜。
3. `03-sentiment-trend-365d.png`：近 365 日情感时间河。
4. `04-alert-radar.png`：生产告警雷达。
5. `05-model-diagnostics.png`：星级预测矩阵、置信度和负面方面。
6. `06-agent-drawer.png`：ReviewOps Copilot 调查面板。
7. `07-agent-risk-investigation.png`：真实 warehouse 风险商品证据链。
8. `manifest.json`：生成时间、数据契约、视口和浏览器验证结果。

自动化模拟用户截图所处的 Windows 浏览器布局：使用 1440×687 CSS
可视区，并通过 2× 像素密度生成 2880×1374 的高清纯网页截图（不包含浏览器
工具栏和 Windows 任务栏）。这不是对低分辨率图片进行放大，页面文字、ECharts
图表和边框均由浏览器直接进行高清渲染。总览会切换到“近 365 日”，并将 Agent
按钮放在右上区域。控制台错误或 API 请求失败时脚本会返回失败。
