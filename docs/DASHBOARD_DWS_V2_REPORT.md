# 电商评论情感分析 DWS v2 扩展报告

## 1. 扩展目的

本次在 production-v1 三张 DWS 基础上新增十张真实数据聚合表，为分类、店铺、购买验证、评分矩阵、置信度、月度趋势、风险告警、安全评论卡片、方面词规则和差评原因词规则提供稳定的 MySQL serving 数据源。

## 2. 数据来源

- Hive 数据库：`review_dw`
- 批次：`prod_v1_100k`
- 模型版本：`tfidf_logreg_oof_v1`
- 生产关联视图：`vw_dwd_review_with_sentiment`
- 实测关联记录：99,703 条
- 总体情感：正向 64,861、中性 18,943、负向 15,899

非文本指标来自生产关联视图。方面、差评原因和安全样例使用 DWD 评论与真实 OOF 预测的只读关联；输出不包含 `user_id`、完整 `review_key` 或无限长度评论正文。

## 3. 原有三张 DWS

| 表 | Hive 行数 | MySQL 行数 | 状态 |
|---|---:|---:|---|
| `dws_sentiment_overview` | 1 | 1 | 保持不变 |
| `dws_sentiment_daily` | 4,137 | 4,137 | 保持不变 |
| `dws_product_sentiment` | 76,784 | 76,784 | 保持不变 |

overview 的 `review_count=99,703`，证明 v2 同步未破坏原有生产结果。

## 4. 新增十张 DWS

| 表 | 粒度 | Hive 行数 | MySQL 行数 | 用途 |
|---|---|---:|---:|---|
| `dws_category_sentiment` | 分类 + 批次 + 模型 | 1 | 1 | 分类情感比较 |
| `dws_store_sentiment` | 店铺 + 批次 + 模型 | 24,269 | 24,269 | 店铺评论量和负向率排行 |
| `dws_verified_purchase_sentiment` | 购买验证状态 + 批次 + 模型 | 2 | 2 | 已验证/未验证购买比较 |
| `dws_rating_prediction_matrix` | 星级 + 预测标签 + 批次 + 模型 | 15 | 15 | 5×3 情感热力图 |
| `dws_prediction_confidence` | 置信度桶 + 批次 + 模型 | 4 | 4 | 预测置信度分布 |
| `dws_monthly_sentiment` | 月份 + 批次 + 模型 | 200 | 200 | 月度趋势 |
| `dws_sentiment_alerts` | 单条告警 | 179 | 179 | 风险告警列表 |
| `dws_review_samples` | 安全样例 + 批次 + 模型 | 150 | 150 | 代表性评论卡片 |
| `dws_aspect_summary` | 方面 + 批次 + 模型 | 8 | 8 | 词规则方面汇总 |
| `dws_negative_reasons` | 差评原因 + 批次 + 模型 | 9 | 9 | 词规则差评原因汇总 |

## 5. Hive 构建与校验结果

十张表均只覆盖目标静态分区。分类、店铺、购买验证、评分矩阵、置信度和月度表的评论数均与源数据 99,703 对齐。评分矩阵每个星级的三类比例和为 1；非法比例行、非目标批次/模型行均为 0。

实测分布：

- 购买验证：verified 86,927，unverified 12,776；
- 置信度：low 11,354，medium 34,125，high 24,340，very_high 29,884；
- 安全样例：negative、neutral、positive 各 50 条；
- 复合主键重复组：0。

## 6. MySQL 同步与 Hive/MySQL 对账

十张新表在同一事务中按目标批次和模型替换；失败时回滚。原三张表未执行删除或替换。13 张表的 Hive/MySQL 行数逐表一致，最终 reconciliation 为 `PASS`。

## 7. 方面规则说明

`dws_aspect_summary` 是确定性规则提取，不是 LLM、BERT 或学习型方面模型：

- `extraction_method=keyword_rules_v1`
- `rule_version=fashion_aspects_v1`

| 方面 | 命中数 | 正向 | 中性 | 负向 |
|---|---:|---:|---:|---:|
| appearance | 38,475 | 25,202 | 8,479 | 4,794 |
| comfort | 15,838 | 12,194 | 2,641 | 1,003 |
| durability | 3,632 | 1,811 | 594 | 1,227 |
| material | 15,041 | 7,897 | 4,343 | 2,801 |
| price_value | 14,564 | 8,598 | 2,836 | 3,130 |
| quality | 14,114 | 9,485 | 2,469 | 2,160 |
| shipping_packaging | 3,888 | 2,409 | 594 | 885 |
| size_fit | 35,897 | 21,676 | 8,760 | 5,461 |

一条评论可命中多个方面，但每条评论在同一方面最多计数一次，因此总命中 141,449 可以大于评论数。

## 8. 差评原因规则说明

`dws_negative_reasons` 仅对 15,899 条负向预测应用确定性规则：

- `extraction_method=keyword_rules_v1`
- `rule_version=negative_reasons_v1`

| 原因 | 命中数 | 产品数 | 占负向评论比例 |
|---|---:|---:|---:|
| color_mismatch | 141 | 140 | 0.8868% |
| damaged_item | 467 | 461 | 2.9373% |
| delivery_issue | 3 | 3 | 0.0189% |
| not_as_described | 45 | 45 | 0.2830% |
| overpriced | 533 | 528 | 3.3524% |
| poor_quality | 1,068 | 1,059 | 6.7174% |
| return_issue | 2,700 | 2,651 | 16.9822% |
| uncomfortable | 439 | 430 | 2.7612% |
| wrong_size | 2,645 | 2,578 | 16.6363% |

每条负向评论可命中多个原因，但同一原因最多计数一次；总命中为 8,041。

## 9. 样例评论脱敏说明

样例按 `pred_score DESC, review_key` 确定性排序，每个标签最多 50 条。`sample_id` 为 review key 的 SHA-256；预览清除制表符、换行和控制字符，最大 180 个字符。实测 150 条样例全部满足限制，无重复键、无测试行标记，不输出完整评论键或用户字段。

## 10. 告警规则

| 规则 | 实测告警数 |
|---|---:|
| `DAILY_NEGATIVE_SPIKE` | 125 |
| `PRODUCT_HIGH_NEGATIVE_RATE` | 30 |
| `PRODUCT_LOW_CONFIDENCE` | 6 |
| `PRODUCT_LOW_RATING` | 18 |
| `CATEGORY_NEGATIVE_RISK` | 0 |

总计 179 条，全部由生产聚合指标和固定阈值确定性生成，alert ID 无重复。

## 11. 前端可视化建议

- KPI 与趋势继续使用 `/api/overview`、`/api/trends/daily`；
- 新增分类、店铺、购买验证、评分热力图、置信度和月度趋势组件；
- `/api/alerts` 用于告警列表和级别筛选；
- `/api/samples` 仅展示已脱敏的受限预览；
- `/api/aspects` 与 `/api/negative-reasons` 必须标注为 `keyword_rules_v1`。

完整路由与粒度见 `docs/MYSQL_SERVING_V2_TABLE_MANIFEST.md`。

## 12. 安全说明

- 未重训模型、未导入新预测、未改写 ODS/DWD；
- 未删除或重建 MySQL 容器和数据卷；
- SQL dump 精确包含 13 张 serving 表，不含账户、授权、密码环境变量名或用户字段；
- 导出数据、dump、ZIP、本地连接文件均保持忽略且不进入 Git；
- v2 SQL 使用参数化写入、合理分块、单事务和失败回滚。

## 13. 局限性

方面和差评原因是可解释的关键词规则，存在词义歧义、否定语境和未覆盖表达，不代表训练模型结果。样例仅用于可视化展示，不是完整评论数据集。后续可在独立版本中评估学习型方面模型，但不得将其与本次规则结果混称。

## 14. 验收结论

Hive 十张新增表、MySQL 十张新增表、原有三张生产表、13 表逐表对账、安全样例、规则元数据以及 production-v2 交付包均通过实测验收。
