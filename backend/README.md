# Stage G backend (smoke-first)

FastAPI 指标服务：供大屏与后续 Agent 共用。默认读取 `exports/agent/smoke/`。

完整复现步骤见：`docs/阶段G_冒烟运行手册.md`。

## 启动顺序

1. **先**运行本目录 `start.bat`（端口 **8080**）  
2. 再运行 `dashboard\start.bat`（端口 **5173**）

也可在仓库根执行 `start_smoke_demo.bat` 一次开两个窗口。

## 首次安装

在仓库根：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
copy backend\.env.example .env
backend\start.bat
```

## 配置

| 变量 | 含义 |
|------|------|
| `DATA_MODE=smoke` | 冒烟：读 JSON 导出（默认） |
| `DATA_MODE=warehouse` | 正式：读队友 MySQL 服务库（Hive DWS 同步） |
| `SMOKE_EXPORT_DIR` | 相对仓库根，默认 `exports/agent/smoke` |
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_DATABASE` | 服务库地址 |
| `MYSQL_USER` / `MYSQL_PASSWORD` | **只用** `agent_reader`（拒绝 root） |
| `WAREHOUSE_LOAD_BATCH_ID` | 默认 `prod_v1_100k` |
| `WAREHOUSE_MODEL_VERSION` | 默认 `tfidf_logreg_oof_v1` |
| `CORS_ORIGINS` | 需包含 `http://127.0.0.1:5173` |

密钥写在 `backend/.env`（已 gitignore），勿提交密码。

## 正式 warehouse 启动

1. 确认局域网可达：`Test-NetConnection <MYSQL_HOST> -Port 3306`  
2. 填写 `backend/.env`（可参考 `.env.example`）  
3. 安装依赖后运行连通检查：

```bat
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.venv\Scripts\python.exe backend\scripts\check_mysql_serving.py
backend\start_warehouse.bat
```

## 接口

契约：`docs/api_contract_v0.md`

- smoke / warehouse：`/api/health` `/api/kpi` `/api/top-negative-products`
- warehouse v2：`/api/trend` `/api/trends/monthly` `/api/aspects` `/api/negative-reasons` `/api/alerts` `/api/samples`
- warehouse v2 扩展：`/api/categories` `/api/stores` `/api/verified-purchase` `/api/rating-matrix` `/api/confidence`
- smoke 下扩展接口多为 501

## 错误态

- 导出目录缺失或文件损坏：启动校验失败 / 接口 500  
- MySQL 不可达：`upstream_unavailable`  
- 占位 / 未同步能力：501（禁止返回假全 0 成功数据）

## 冒烟声明

smoke：`production_business_metrics=false`。  
warehouse：`production_business_metrics=true`，数据来自 MySQL 服务库只读账号。
