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

当前本机连接信息（不含密码）：

- LAN 主机：`10.38.193.232`
- 端口：`3306`
- 数据库：`shopreview_serving`
- 只读用户：`agent_reader`

## 二、只读账户

不要让 Agent 使用 MySQL `root` 或同步 writer 账户。当前已创建临时 LAN 兼容账户 `agent_reader@'%'`，实测授权只有：

```sql
GRANT USAGE ON *.* TO `agent_reader`@`%`;
GRANT SELECT ON `shopreview_serving`.* TO `agent_reader`@`%`;
```

该账户没有 INSERT、UPDATE、DELETE、CREATE、DROP 或 ALTER 权限。确定 Agent 笔记本的 LAN IP 后，应由管理员重新创建或迁移为具体来源地址的 `agent_reader@'AGENT_LAN_IP'`。同机运行时优先使用 `localhost`。

## 三、安全要求

- 不要把真实密码写入 Git、README、脚本参数或前端代码；
- 使用被 Git 忽略的 `.env.mysql.local` 保存本机配置；
- reader 连接信息位于被忽略的 `.env.mysql.agent.local`；密码应通过私密渠道交付，不得复制到聊天群、Git 或报告；
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

本机与 LAN IP 的 3306 TCP 测试均已通过，网络就绪状态为 READY。MySQL 数据与账户已准备好，但 FastAPI/Agent 实时集成仍待 Agent 开发者完成。
