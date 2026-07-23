# Stage G 冒烟一键运行手册

给队友复现用。冒烟数据 **不是** 生产业务指标。

## 端口

| 服务 | 地址 |
|------|------|
| FastAPI | http://127.0.0.1:8080 |
| 大屏 | http://127.0.0.1:5173 |

## 启动顺序（必须）

1. **先**启动后端  
2. **再**启动大屏  
3. 浏览器打开 http://127.0.0.1:5173  

### 方式 A：两个窗口脚本

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
backend\start.bat
```

另开一个终端：

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
dashboard\start.bat
```

### 方式 B：一键开两个窗口

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
start_smoke_demo.bat
```

## 首次依赖

```bat
cd /d F:\Production_Internship\ShopReview_NLP_Agent
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
copy backend\.env.example .env

cd dashboard
copy .env.example .env
npm.cmd install
```

## 配置

| 位置 | 变量 | 含义 |
|------|------|------|
| 仓库根 / backend 环境 | `DATA_MODE=smoke` | 读 `exports/agent/smoke` |
| 同上 | `DATA_MODE=warehouse` | 正式版占位（尚未实现） |
| `dashboard/.env` | `VITE_API_BASE=http://127.0.0.1:8080` | 大屏只打 API |

正式 DWS 就绪后：实现 `WarehouseProvider`，改 `DATA_MODE=warehouse`，**路由不变**。

## 错误态自测（步骤 6）

1. **断后端**：关掉 API 窗口 → 大屏点「刷新」→ 应出现红色「后端不可用」提示，**不能**继续显示旧假数顶上。  
2. **占位接口**：API 开着时访问  
   - http://127.0.0.1:8080/api/trend  
   - http://127.0.0.1:8080/api/alerts  
   - http://127.0.0.1:8080/api/samples  
   期望：**HTTP 501** + `error=not_available_in_smoke`。大屏能力条显示「暂未接入」。

## 健康检查

```bat
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/kpi
```

更多 curl：`docs/phase_G_api_smoke_commands.md`  
契约：`docs/api_contract_v0.md`
