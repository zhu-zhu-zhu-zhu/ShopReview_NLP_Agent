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
| overview | 1 | 1 | PENDING |
| daily | 4,137 | 4,137 | PENDING |
| product | 76,784 | 76,784 | PENDING |

overview 的 `review_count` 为 99,703。本次 Hive ExportOnly 已完成；MySQL 3306 未监听且 writer 凭据未配置，因此没有连接或修改 MySQL。

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

当前只执行到本地安全导出和 Python 校验。MySQL 事务与最终对账尚未执行。

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
| Hive/MySQL 对账 | PENDING |

## 七、Agent 连接方式

后续采用 `MySQL → FastAPI → Agent`。Agent 只调用 FastAPI 暴露的受控查询工具，不使用 root，也不直接访问 Hive。

## 八、安全说明

- Agent 必须使用专用只读账户；
- writer 与 reader 密码均不得进入 Git；
- MySQL 3306 不得暴露到公共互联网；
- 本次没有同步原始评论、评论文本、DWD 明细或用户标识；
- `.env.mysql.local` 和本地导出目录由 Git 忽略。

## 九、限制

- 当前只覆盖一个 production batch/model；
- MySQL Server 与 writer 凭据尚未配置；
- MySQL 同步和 Hive/MySQL 最终对账仍为 PENDING；
- MySQL 是服务副本，Hive DWS 仍是权威来源。

## 十、验收结果

Hive DWS 导出及本地文件校验通过。由于 MySQL 不可用，不报告 MySQL PASS。

HIVE DWS EXPORT RESULT: PASS

LOCAL EXPORT VALIDATION RESULT: PASS

MYSQL SERVING SYNC RESULT: PENDING

HIVE MYSQL RECONCILIATION RESULT: PENDING

CREDENTIAL SAFETY RESULT: PASS
