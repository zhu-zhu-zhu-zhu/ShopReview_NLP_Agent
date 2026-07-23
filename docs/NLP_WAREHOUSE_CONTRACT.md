# NLP–Warehouse Production Contract

## 1. Contract version

- Contract：`production_v1`
- Batch：`prod_v1_100k`
- Evaluation model：`tfidf_logreg_v1`
- Official warehouse prediction model：`tfidf_logreg_oof_v1`
- Status：Implemented and validated

## 2. Warehouse → NLP input

固定字段顺序：

| Field | Type | Requirement |
|---|---|---|
| `review_key` | string | 必填、非空、全批次唯一 |
| `review_text_clean` | string | 必填、非空；唯一模型特征 |
| `rating_label` | enum | `negative`、`neutral`、`positive` |
| `rating` | number | 1.0～5.0 |
| `parent_asin` | string | production-v1 中非空 |
| `main_category` | string | production-v1 中非空 |
| `review_time` | timestamp | 已解析评论时间 |
| `load_batch_id` | string | 固定 `prod_v1_100k` |

禁止包含 `user_id`。`rating_label` 由星级映射生成，是弱监督目标，不是模型预测或人工真值。

## 3. Stable review key

`review_key` 是以下文本按 UTF-8 编码后的 lowercase SHA-256：

```text
user_id + "|#|" + asin + "|#|" + parent_asin + "|#|" + timestamp + "|#|" + title + "|#|" + text
```

缺失值按空字符串参与拼接。有意义的原始标题和评论文本在键生成前不做 trim。NLP 模块必须原样返回键，不得重新计算、标准化或格式化。

## 4. Official OOF prediction output

每行必须且只能包含：

| Field | Type | Rule |
|---|---|---|
| `review_key` | string | 必须存在于本批 DWD |
| `pred_label` | enum | `negative`、`neutral`、`positive` |
| `pred_score` | decimal | `pred_label` 对应概率，0～1 |
| `negative_score` | decimal | 0～1 |
| `neutral_score` | decimal | 0～1 |
| `positive_score` | decimal | 0～1 |
| `model_version` | string | 固定 `tfidf_logreg_oof_v1` |
| `inferred_at` | UTC timestamp | 合法 ISO-8601 |

概率约束：

- 三类概率之和近似 1；
- `pred_label` 必须为最大概率对应标签；
- `pred_score` 必须等于 `pred_label` 对应概率；
- 不得包含 `rating`、`rating_label`、`review_text`、`review_text_clean` 或 `user_id`。

## 5. OOF generation rule

- `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`；
- 每条评论只能由未训练过该评论的折模型预测；
- 预测按输入顺序回填；
- 五折合计必须覆盖 99,703 个唯一 `review_key`；
- 不能用全量训练模型为同一批训练记录生成正式数仓预测。

## 6. Write-back validation

| Check | Production result |
|---|---:|
| 物理行 | 99,703 |
| 合法预测 | 99,703 |
| 唯一键 | 99,703 |
| duplicate | 0 |
| missing key | 0 |
| unknown key | 0 |
| coverage | 100% |
| 非法标签/概率/时间 | 0 |
| 禁止字段 | 0 |

正式预测文件 SHA-256：

`6f864870573275f38a610b3d9c6b0bed3250e208061d81d2fc45edfc20f40f95`

## 7. Hive objects

- `review_dw.dwd_amazon_fashion_review`
- `review_dw.stg_nlp_predictions`
- `review_dw.dwd_review_sentiment`
- `review_dw.vw_dwd_review_with_sentiment`

写回唯一性为 `(review_key, model_version)`。未知键、重复键、非法记录必须在写入正式 DWD 前失败。

## 8. Final full-data model

`models/tfidf_logreg_v1.joblib` 使用全部 99,703 条弱标注记录训练，仅用于未来未见评论推理：

- training rows：99,703；
- selected `C=0.5`；
- model SHA-256：`f3be40026a352dd279691ed7f1dc99665f997be6b367a3f7614e2d32555496db`；
- `used_for_official_oof_predictions=false`。

模型工件必须被 Git 忽略。

## 9. Responsibility boundary

Warehouse：

- 生成稳定键和清洗文本；
- 导出固定 schema；
- 校验覆盖、唯一性、概率和禁止字段；
- 导入预测并构建 DWS。

NLP：

- 仅使用训练/验证数据选参；
- 对 untouched test 只评估一次；
- 生成严格 OOF 正式预测；
- 保存全量未来推理模型；
- 不独立修改 Hive schema。
