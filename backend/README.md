# ShopReview Production Metrics API

FastAPI 服务通过只读 `agent_reader` 查询 `shopreview_serving`，为大屏和 Agent 提供 `prod_v1_100k` + `tfidf_logreg_oof_v1` 的 production serving v2 指标。

## 配置

复制 `backend/.env.example` 为 `backend/.env`，只在本机填入现有只读密码：

```env
DATA_MODE=warehouse
API_HOST=127.0.0.1
API_PORT=8080
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=agent_reader
MYSQL_PASSWORD=
MYSQL_DATABASE=shopreview_serving
WAREHOUSE_LOAD_BATCH_ID=prod_v1_100k
WAREHOUSE_MODEL_VERSION=tfidf_logreg_oof_v1
```

`backend/.env` 被 Git 忽略。应用层会拒绝 `MYSQL_USER=root`。

## 启动与健康检查

```powershell
cd D:\bdt-app-course\projects\ShopReview_NLP_Agent
.\.venv\Scripts\python.exe backend\scripts\check_mysql_serving.py
.\backend\start_warehouse.bat
```

访问 `http://127.0.0.1:8080/docs`。启动时 MySQL 暂时不可用不会伪造数据，业务接口会返回 `upstream_unavailable`。

## 数据访问约束

- provider 唯一实现为 `WarehouseProvider`；
- 所有业务查询同时过滤 `load_batch_id` 与 `model_version`；
- 查询参数通过 MySQL driver 参数化；
- 用户输入不能控制表名；
- API 只读，不包含 INSERT、UPDATE、DELETE 或 DDL；
- 所有成功响应标记 `data_mode=warehouse`、`schema_version=serving_v2` 和 `production_business_metrics=true`。

## 接口

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/health` | 批次、模型、13 张表行数与来源 |
| GET | `/api/kpi` | 总评论量、情感分布、评分和置信度 |
| GET | `/api/trend` | 日趋势；支持日期、limit 或 recent_days |
| GET | `/api/trends/monthly` | 月度趋势 |
| GET | `/api/top-negative-products` | 商品差评榜 |
| GET | `/api/top-positive-products` | 商品好评榜 |
| GET | `/api/stores` | 店铺差评榜 |
| GET | `/api/top-positive-stores` | 店铺好评榜 |
| GET | `/api/categories` | 品类指标 |
| GET | `/api/verified-purchase` | 认证购买对比 |
| GET | `/api/rating-matrix` | 星级 × 预测矩阵 |
| GET | `/api/confidence` | 预测置信度分桶 |
| GET | `/api/aspects` | 规则方面统计 |
| GET | `/api/negative-reasons` | 全局负面原因 |
| GET | `/api/alerts` | 风险告警 |
| GET | `/api/samples` | 脱敏评论样例 |
| POST | `/api/agent/chat` | DeepSeek Agent 调查 |

详细参数、字段与错误响应见 [API_REFERENCE.md](../docs/API_REFERENCE.md)。
