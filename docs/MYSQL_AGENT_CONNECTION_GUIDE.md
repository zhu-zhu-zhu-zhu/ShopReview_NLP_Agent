# MySQL Agent 只读连接指南

## 一、服务层范围

MySQL 数据库为 `shopreview_serving`，仅提供以下三张聚合服务表：

- `dws_sentiment_overview`
- `dws_sentiment_daily`
- `dws_product_sentiment`

当前固定生产范围为：

- `load_batch_id = prod_v1_100k`
- `model_version = tfidf_logreg_oof_v1`

MySQL 只保存 Hive DWS 的聚合副本，不包含原始评论、评论明细或用户标识。推荐调用链为：

```text
Hive DWS → MySQL serving copy → FastAPI → Agent
```

## 二、只读账户

不要让 Agent 使用 MySQL `root` 或同步 writer 账户。MySQL 管理员应在服务器配置完成后手工创建只读账户，并替换下面的主机和密码占位符：

```sql
CREATE USER 'agent_reader'@'SPECIFIC_HOST'
IDENTIFIED BY 'SET_A_STRONG_PASSWORD';

GRANT SELECT ON shopreview_serving.*
TO 'agent_reader'@'SPECIFIC_HOST';

FLUSH PRIVILEGES;
```

Agent 与 MySQL 在同一台电脑时，优先把 `SPECIFIC_HOST` 设置为 `localhost`。Agent 在另一台局域网电脑时，应使用该电脑的具体 LAN IP。除非确实没有更安全的替代方案，否则不要使用 `%`。

## 三、安全要求

- 不要把真实密码写入 Git、README、脚本参数或前端代码；
- 使用被 Git 忽略的 `.env.mysql.local` 保存本机配置；
- 不要把 3306 端口暴露到公共互联网；
- FastAPI 应使用参数化只读查询，并固定查询生产 batch/model；
- Agent 只通过 FastAPI 工具读取聚合结果，不应直接获得数据库管理员权限。

## 四、只读连通性测试

完成只读账户配置后，可在 MySQL 客户端中执行：

```sql
SELECT review_count, positive_rate, neutral_rate, negative_rate
FROM shopreview_serving.dws_sentiment_overview
WHERE load_batch_id='prod_v1_100k'
  AND model_version='tfidf_logreg_oof_v1';
```

当前 MySQL Server 和账户尚未配置，因此本指南只提供后续安全连接模板，不代表 Agent 已实时接入。
