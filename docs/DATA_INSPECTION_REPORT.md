# Amazon Fashion 数据集检查报告

> **本报告仅为有界样本检查结果，不代表完整数据集统计。**

## 一、数据检查概况

本阶段对 Amazon Fashion 评论数据进行了快速质量检查，共检查 100,000 条评论记录和 50,000 条商品元数据记录。检查范围内未发现畸形 JSON 和空行，评论文本缺失、null 或空白记录共 24 条。

评分数据以 5 星评论为主。按星级生成的 weak label（弱情感标签）中，positive 73,370 条、neutral 10,947 条、negative 15,683 条。

**以上结果仅来自有界检查范围，不代表完整数据集统计。**

## 二、检查范围

- 评论文件：检查前 100,000 个物理行；
- 商品元数据文件：检查前 50,000 个物理行；
- 本次检查采用限定范围，不是全量扫描。

## 三、源文件信息

| 文件 | 大小 |
|---|---:|
| `Amazon_Fashion.jsonl` | 1,051,324,731 bytes |
| `meta_Amazon_Fashion.jsonl` | 1,422,365,805 bytes |

## 四、检查方法

- 使用 Python 标准库解析 JSON，按行读取 JSONL；
- 文件编码为 UTF-8，原始文件保持只读；
- 未使用 pandas 将完整文件加载到内存；
- 本地抽样采用 reservoir sampling（蓄水池抽样），`seed=42`；
- Phase B 检查阶段未使用 HDFS、Hive 或 NLP 模型。

## 五、评论数据检查结果

| 检查指标 | 结果 |
|---|---:|
| 检查物理行数 | 100,000 |
| 合法 JSON 对象 | 100,000 |
| 畸形 JSON | 0 |
| 空行 | 0 |
| 缺失、null 或空白评论文本 | 24 |
| 最早 `timestamp`（UTC） | 2003-06-19T23:07:30+00:00 |
| 最晚 `timestamp`（UTC） | 2023-03-20T04:33:44.379000+00:00 |
| `helpful_vote` 有效数量 | 100,000 |
| `helpful_vote` 无效或缺失数量 | 0 |
| `helpful_vote` 最小值 | 0.0 |
| `helpful_vote` 最大值 | 454.0 |
| `helpful_vote` 平均值 | 0.66438 |
| `verified_purchase=false` | 12,814 |
| `verified_purchase=true` | 87,186 |

## 六、商品元数据检查结果

| 检查指标 | 结果 |
|---|---:|
| 检查物理行数 | 50,000 |
| 合法 JSON 对象 | 50,000 |
| 畸形 JSON | 0 |
| 空行 | 0 |

## 七、实际观察到的字段

### 评论数据字段

`asin`、`helpful_vote`、`images`、`parent_asin`、`rating`、`text`、`timestamp`、`title`、`user_id`、`verified_purchase`

### 商品元数据字段

`average_rating`、`bought_together`、`categories`、`description`、`details`、`features`、`images`、`main_category`、`parent_asin`、`price`、`rating_number`、`store`、`title`、`videos`

**以上字段仅是在本次有界检查范围内实际观察到的字段。**

## 八、评分与弱情感标签分布

### 评分分布

| 评分 | 数量 |
|---:|---:|
| 1 星 | 9,010 |
| 2 星 | 6,673 |
| 3 星 | 10,947 |
| 4 星 | 16,424 |
| 5 星 | 56,946 |

### 弱情感标签（weak label）分布

| 弱情感标签 | 星级规则 | 数量 |
|---|---|---:|
| negative | 1–2 星 | 15,683 |
| neutral | 3 星 | 10,947 |
| positive | 4–5 星 | 73,370 |

**weak label 由 `rating` 星级映射生成，不是 NLP 模型预测结果。**

## 九、parent_asin 关联检查

| 指标 | 结果 |
|---|---:|
| 非空 `parent_asin` 评论数 | 100,000 |
| 匹配当前元数据检查范围的评论数 | 11,516 |
| 有界样本关联率 | 11.516000% |

该结果只比较评论文件前 100,000 行与元数据文件前 50,000 行。

**11.516000% 不是完整数据集关联率。**

## 十、本地样本生成

- 评论样本：100 条；
- 商品元数据样本：100 条；
- 随机种子：`seed=42`；
- 抽样方法：reservoir sampling；
- 样本保留在本地并被 Git 忽略，未提交到仓库。

## 十一、对数仓设计的影响

- 评论数据和商品元数据分别建立 ODS 表；
- 使用 `parent_asin` 关联评论与商品元数据；
- DWD 层需要转换 `timestamp`；
- DWD 层需要明确处理空评论文本；
- 商品元数据字段需要支持空值；
- `rating` 可以映射为 weak label；
- Hive 字段类型仍为 Draft，需后续继续验证。

## 十二、局限性

- 本报告只检查了有界数据范围，不是完整数据集统计；
- 尚未完成完整数据集的 distinct（去重计数）、duplicate（重复）和 join（关联）精确统计；
- Phase B 检查阶段未执行 NLP 模型；
- Phase B 检查阶段未执行 HDFS 或 Hive；
- 本报告反映的是 Phase B 数据检查阶段，不能替代后续入仓和全量验证结果。

## 十三、下一步

在团队确认数据范围和字段后，继续准备正式 HDFS 数据落盘方式、Hive ODS 表结构和后续 DWD 清洗规则。

> **本报告仅为有界样本检查结果，不代表完整数据集统计。**
