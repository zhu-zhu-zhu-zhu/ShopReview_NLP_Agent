# Amazon Fashion 生产版 ODS/DWD v1 验收报告

> **本报告对应 production-v1 实验范围，不代表完整 Amazon Fashion 数据集统计。**

## 一、生产数据范围

| 项目 | 实测结果 |
|---|---:|
| 批次 ID | `prod_v1_100k` |
| 评论选择上限 | 前 100,000 个合法 JSON 对象 |
| 评论物理扫描行数 | 100,000 |
| 合法评论记录 | 100,000 |
| 评论畸形行 / 空行 | 0 / 0 |
| 唯一 `parent_asin` | 76,802 |
| 元数据物理扫描行数 | 794,759 |
| 合法元数据对象 | 794,759 |
| 匹配元数据 | 76,802 |
| 缺失元数据 `parent_asin` | 0 |

元数据按照评论集合中的 `parent_asin` 提取。找到全部 76,802 个目标后停止扫描，没有对完整 Amazon Fashion 数据集做全量统计。

## 二、数据准备方式

- 使用 Python 标准库逐行读取 UTF-8 JSONL，没有使用 pandas 全量加载；
- 评论记录边读取边转换并写出，内存中只保留唯一 `parent_asin` 集合；
- 元数据只保留每个目标 `parent_asin` 的首个对象；
- Hive 输入采用 ASCII control-A（`0x01`）分隔；
- null 使用 `\N`，嵌套列表和对象使用紧凑 JSON；
- control-A、回车、换行和制表符在字段内转换为安全空格。

生成的生产源文件保存在被 Git 忽略的 `data/processed/production_v1/`，未提交仓库。

## 三、HDFS Paths

- `/data/review_dw/ods/amazon_fashion_review/load_batch_id=prod_v1_100k`
- `/data/review_dw/ods/amazon_fashion_meta/load_batch_id=prod_v1_100k`

每个批次目录最终只有一个对应的 production-v1 文本文件。原始 JSONL 未上传，`/data/review_dw/smoke/` 与 `/data/review_dw/smoke_d/` 未修改。

## 四、ODS Tables

| Hive 表 | 分区 | 行数 |
|---|---|---:|
| `review_dw.ods_amazon_fashion_review` | `load_batch_id=prod_v1_100k` | 100,000 |
| `review_dw.ods_amazon_fashion_meta` | `load_batch_id=prod_v1_100k` | 76,802 |

- 评论与元数据的 distinct `parent_asin` 均为 76,802；
- 100,000 条 ODS 评论均匹配元数据，未匹配评论为 0；
- ODS 元数据匹配率为 100.000000%。

## 五、DWD Cleaning

- 过滤 null 或空白评论文本，同时保留原始 `review_text`；
- 对清洗文本执行首尾空白删除、控制字符替换和连续空白合并；
- 将毫秒 `review_timestamp` 转换为 `review_time`、`dt` 和 `review_year`；
- 按规定字段拼接后生成 SHA-256 `review_key`；
- 将星级映射为 `negative`、`neutral`、`positive` weak label；
- 使用 LEFT JOIN 保留评论，并通过 `metadata_matched` 标记元数据覆盖；
- 对相同 `review_key` 的源端精确重复记录保留一条；
- 使用 Parquet 存储，按 `load_batch_id` 和 `review_year` 分区。

## 六、Validation Results

| 对账项目 | 实测结果 |
|---|---:|
| ODS 评论 | 100,000 |
| ODS 空文本 | 24 |
| ODS 非空文本记录 | 99,976 |
| 源端重复 `review_key` 组 | 273 |
| 源端重复冗余行 | 273 |
| 去重后预期 DWD | 99,703 |
| 实际 DWD | 99,703 |

对账公式：`100,000 - 24 - 273 = 99,703`。实际 DWD 与去重后的预期记录数完全一致。

### weak label 分布

| 标签 | DWD 行数 |
|---|---:|
| negative | 15,640 |
| neutral | 10,913 |
| positive | 73,150 |

这些标签由 `rating` 映射生成，不是 NLP 模型预测结果。

### DWD 年份分区

批次 `prod_v1_100k` 共生成 21 个年份分区，范围为 2003–2023。所有分区都只属于该生产实验批次。

## 七、Data Quality

| 检查项 | 结果 |
|---|---:|
| DWD null / 空白 `review_key` | 0 |
| DWD 重复 `review_key` 组 | 0 |
| 空白 `review_text_clean` | 0 |
| 非法 `rating_label` | 0 |
| 有效时间转换 | 99,703 |
| 无效时间转换 | 0 |
| `metadata_matched=true` | 99,703 |
| `metadata_matched=false` | 0 |
| `product_title` 非空 | 99,703 |
| `store_name` 非空 | 99,703 |
| `main_category` 非空 | 99,703 |

发现的主要质量问题是 273 组源端精确重复评论。严重度为中，置信度高：若不处理会破坏 `review_key` 唯一性并影响后续预测写回。production-v1 已在 DWD 保留每组一条，ODS 仍完整保留全部源记录以便追溯。

## 八、Limitations

- production-v1 只使用前 100,000 个合法评论对象，不是完整数据集；
- 元数据只提取该评论范围需要的商品；
- `rating_label` 是评分弱标签，不是真实 NLP 预测；
- 尚未导入真实模型预测，也未执行真实方面提取；
- 尚未建设 production DWS、FastAPI、Dashboard 或最终 Agent 集成。

## 九、Result

生产 ODS 行数、批次分区和 HDFS 文件验证通过。DWD 完成空文本过滤、源重复去除、时间转换、元数据关联、weak label 生成和分区写入，各项对账及质量门槛通过。

PRODUCTION ODS RESULT: PASS

PRODUCTION DWD RESULT: PASS
