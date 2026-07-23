# Amazon Fashion NLP 输入交付与正式预测写回报告

## 1. 范围

| 项目 | 结果 |
|---|---:|
| Hive 来源 | `review_dw.dwd_amazon_fashion_review` |
| 批次 | `prod_v1_100k` |
| DWD / eligible / 导出 | 99,703 / 99,703 / 99,703 |
| 正式预测模型 | `tfidf_logreg_oof_v1` |
| 正式预测方式 | 5-fold Stratified OOF |
| 预测行数 | 99,703 |
| 覆盖率 | 100% |

production-v1 是正式实验子集，不代表完整 Amazon Fashion。

## 2. NLP 输入

字段固定为：

`review_key`、`review_text_clean`、`rating_label`、`rating`、`parent_asin`、`main_category`、`review_time`、`load_batch_id`。

输入不包含 `user_id`。`review_text_clean` 是唯一模型特征；评分、弱标签、商品和类目不进入 TF-IDF 特征。

### 输入质量

| Check | Result |
|---|---:|
| 唯一 `review_key` | 99,703 |
| duplicate / blank key | 0 / 0 |
| blank text | 0 |
| illegal rating label | 0 |
| negative / neutral / positive weak labels | 15,640 / 10,913 / 73,150 |
| parent/category/time coverage | 100% / 100% / 100% |

输入 JSONL：

- 路径：`data/processed/nlp_production_v1/nlp_input_prod_v1.jsonl`
- 大小：46,005,546 bytes
- SHA-256：`e10925187eea5fc34721778c0a6e2ea5b8c7492a1325fd0c49966dafe3f12714`

真实 JSONL 被 Git 忽略；仓库只保留安全 summary 和 manifest。

## 3. 模型训练和评估

- 算法：TF-IDF unigram+bigram + Logistic Regression；
- 训练/验证/测试：79,762 / 9,970 / 9,971；
- 分层划分：`random_state=42`；
- 选择标准：验证集 macro-F1，其次 accuracy；
- 选中 `C=0.5`；
- untouched test accuracy：0.830408；
- untouched test macro-F1：0.606527；
- untouched test weighted-F1：0.810371。

详细逐类结果见 `NLP_BASELINE_TRAINING_REPORT.md`。

## 4. 正式 OOF 预测

`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`。每条记录由没有训练过它的折模型预测，防止将同批训练内预测作为正式 warehouse 结果。

预测字段：

`review_key`、`pred_label`、`pred_score`、`negative_score`、`neutral_score`、`positive_score`、`model_version`、`inferred_at`。

不得包含 rating、rating_label、评论文本或 user_id。

### Contract validation

| Check | Result |
|---|---:|
| physical / valid rows | 99,703 / 99,703 |
| unique keys | 99,703 |
| duplicate / missing / unknown | 0 / 0 / 0 |
| coverage | 100% |
| invalid labels/scores/timestamps | 0 |
| forbidden/unexpected fields | 0 |
| score min / mean / max | 0.336122 / 0.753397 / 0.999982 |

预测分布：

| Label | Count |
|---|---:|
| negative | 15,899 |
| neutral | 18,943 |
| positive | 64,861 |

正式预测 SHA-256：

`6f864870573275f38a610b3d9c6b0bed3250e208061d81d2fc45edfc20f40f95`

## 5. Hive write-back

预测经过本地契约验证和 control-A 转换后进入：

- `review_dw.stg_nlp_predictions`
- `review_dw.dwd_review_sentiment`
- `review_dw.vw_dwd_review_with_sentiment`

模型分区使用安全映射 `tfidf_logreg_oof_v1_e1bd04f73c2d`，业务 `model_version` 保持 `tfidf_logreg_oof_v1`。写回后 DWD 预测与评论键一一覆盖，并用于 production DWS。

## 6. Full-data model

OOF 完成后，另用 99,703 条记录训练 `models/tfidf_logreg_v1.joblib`，只用于未来未见评论推理，不参与本批正式 OOF。

## 7. Serving result

MySQL serving v2 已同步：

- review_count：99,703；
- positive / neutral / negative：64,861 / 18,943 / 15,899；
- average_prediction_score：0.753397；
- batch/model：`prod_v1_100k` / `tfidf_logreg_oof_v1`。

## 8. Limitations

- 训练目标是星级映射弱标签，不是人工真值；
- neutral 类测试识别能力明显弱于 positive；
- 基线训练存在达到 `max_iter=1000` 的收敛警告；
- OOF 解决同批 in-sample 预测问题，但不等于线上时间外评估；
- 全量模型只能用于未来新评论。

## 9. Result

NLP INPUT HANDOFF RESULT: PASS

HELD-OUT TEST EVALUATION RESULT: PASS

OOF PREDICTION CONTRACT RESULT: PASS

WAREHOUSE WRITE-BACK RESULT: PASS

MYSQL SERVING RECONCILIATION RESULT: PASS
