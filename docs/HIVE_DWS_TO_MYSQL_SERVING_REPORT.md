# Hive DWS 同步 MySQL 服务层报告

## 一、同步目的

Hive DWS 负责 production-v1 的离线数仓计算，MySQL 用作未来 FastAPI 与 Agent 的低延迟聚合查询服务层。Hive 始终是权威数据源，MySQL 只是受控服务副本。

## 二、同步范围

本次只处理以下三张生产聚合表：

- `review_dw.dws_sentiment_overview`
- `review_dw.dws_sentiment_daily`
- `review_dw.dws_product_sentiment`

范围固定为 `load_batch_id=prod_v1_100k`、`model_version=tfidf_logreg_oof_v1`。未导出 ODS、DWD 明细、原始评论、评论文本、用户标识、smoke 或合成数据。

## 三、数据量

| 数据集 | Hive 实测行数 | 本地导出行数 | MySQL 行数 |
|---|---:|---:|---:|
| overview | 1 | 1 | 1 |
| daily | 4,137 | 4,137 | 4,137 |
| product | 76,784 | 76,784 | 76,784 |

overview 的 `review_count` 为 99,703。服务层使用独立 Docker 容器 `shopreview_mysql`、命名卷 `shopreview_mysql_data` 和本机端口 3306，不使用或修改 Hive Metastore MySQL。

## 四、MySQL 表设计

目标库固定为 `shopreview_serving`，使用 `utf8mb4`、`utf8mb4_unicode_ci` 和 InnoDB。三张表分别以 batch/model、日期/batch/model、商品/batch/model 为主键，并为常用的日期、评论量、负向率与类目查询建立索引。正式同步只在一个事务中删除并替换精确 batch/model，不影响其他批次或模型。

## 五、同步流程

```text
Hive Production DWS
→ control-A 分隔的本地安全导出
→ Python schema、数值、比率和主键校验
→ MySQL 三表单事务替换
→ Hive/MySQL 行数与业务总量对账
```

完整流程已执行。同步器只删除精确 batch/model 范围，三表插入与验收位于同一个事务；`ValidateOnly` 随后以只读方式再次通过。

## 六、数据质量

| 检查项 | 结果 |
|---|---:|
| Hive / 本地 overview 行数 | 1 / 1 |
| Hive / 本地 daily 行数 | 4,137 / 4,137 |
| Hive / 本地 product 行数 | 76,784 / 76,784 |
| overview `review_count` | 99,703 |
| 情感计数和与 review_count | PASS |
| 本地主键重复 | 0 |
| 本地非法比率 | 0 |
| MySQL 主键重复 | 0 |
| MySQL 非法比率 | 0 |
| 意外 batch/model | 0 |
| positive / neutral / negative | 64,861 / 18,943 / 15,899 |
| 情感计数合计 | 99,703 |
| Hive/MySQL 对账 | PASS |

## 七、Agent 连接方式

后续采用 `MySQL → FastAPI → Agent`。已创建临时 LAN 兼容的 `agent_reader@'%'`，其授权仅为 `SELECT ON shopreview_serving.*`。确定 Agent 电脑 IP 后，应把来源限制为该具体 LAN IP。

## 八、安全说明

- Agent 必须使用专用只读账户；
- writer 与 reader 密码均不得进入 Git；
- MySQL 3306 不得暴露到公共互联网；
- 本次没有同步原始评论、评论文本、DWD 明细或用户标识；
- `.env.mysql.local` 和本地导出目录由 Git 忽略。
- reader 密码只保存在 `.env.mysql.agent.local` 与本地 handoff 文件中，均由 Git 忽略。

## 九、限制

- 当前只覆盖一个 production batch/model；
- 当前 LAN 主机为 `10.38.193.232:3306`，网络变化后地址可能改变；
- `agent_reader@'%'` 是临时 LAN 兼容配置，应在 Agent 电脑 IP 确定后收紧；
- FastAPI 与 Agent 的实时业务调用尚未执行；
- MySQL 是服务副本，Hive DWS 仍是权威来源。

## 十、验收结果

Hive 导出、本地校验、MySQL 事务同步、业务对账、只读账户和 ValidateOnly 均通过。

HIVE DWS EXPORT RESULT: PASS

LOCAL EXPORT VALIDATION RESULT: PASS

MYSQL SERVING SYNC RESULT: PASS

HIVE MYSQL RECONCILIATION RESULT: PASS

CREDENTIAL SAFETY RESULT: PASS

AGENT READ-ONLY USER RESULT: PASS
