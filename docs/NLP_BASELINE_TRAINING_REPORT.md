# Amazon Fashion 评论情感分类基线模型报告

## 1. 任务与数据

使用 production-v1 的 99,703 条清洗评论完成 negative、neutral、positive 三分类。训练目标 `rating_label` 由星级映射生成；特征只使用 `review_text_clean`。

| Split | Rows | Negative | Neutral | Positive |
|---|---:|---:|---:|---:|
| train | 79,762 | 12,512 | 8,730 | 58,520 |
| validation | 9,970 | 1,564 | 1,091 | 7,315 |
| untouched test | 9,971 | 1,564 | 1,092 | 7,315 |

划分采用分层抽样和 `random_state=42`。

## 2. Pipeline

- `TfidfVectorizer`：lowercase、Unicode accent stripping、1–2 gram、`min_df=2`、`max_df=0.98`、`max_features=50000`、`sublinear_tf=true`、float32；
- 不移除英文停用词，保留否定信息；
- `LogisticRegression(class_weight=balanced, max_iter=1000)`；
- 参数选择只看 validation macro-F1，再以 accuracy 决胜。

## 3. Validation selection

| C | Accuracy | Macro-F1 | Weighted-F1 |
|---:|---:|---:|---:|
| 0.5 | 0.780040 | 0.658552 | 0.802843 |
| 1.0 | 0.761785 | 0.654681 | 0.794140 |
| 2.0 | 0.741123 | 0.599131 | 0.771307 |

最终选择 `C=0.5`。选定后合并 train + validation 重新训练，并只对 untouched test 评估一次。

## 4. Held-out test

| Metric | Value |
|---|---:|
| accuracy | 0.830408 |
| macro precision | 0.656219 |
| macro recall | 0.648331 |
| macro-F1 | 0.606527 |
| weighted-F1 | 0.810371 |

逐类结果：

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| negative | 0.576782 | 0.905371 | 0.704653 | 1,564 |
| neutral | 0.460993 | 0.119048 | 0.189229 | 1,092 |
| positive | 0.930882 | 0.920574 | 0.925699 | 7,315 |

混淆矩阵：

| actual \ predicted | negative | neutral | positive |
|---|---:|---:|---:|
| negative | 1,416 | 35 | 113 |
| neutral | 575 | 130 | 387 |
| positive | 464 | 117 | 6,734 |

neutral recall 只有 0.119048，是当前基线最主要的模型限制。

## 5. Official OOF predictions

- `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`；
- fold holdout：19,941、19,941、19,941、19,940、19,940；
- 每条评论没有出现在预测它的折模型训练集；
- 99,703 行、99,703 唯一键、100% 覆盖；
- model version：`tfidf_logreg_oof_v1`。

OOF 与弱标签比较 accuracy=0.793537、macro-F1=0.667523、weighted-F1=0.813427。该比较使用弱标签，不应解释成人工真值效果。

## 6. Full-data future-inference model

全部 OOF 预测完成后，使用全部 99,703 条弱标注记录训练最终模型：

- artifact：`models/tfidf_logreg_v1.joblib`；
- purpose：future unseen-review inference only；
- artifact SHA-256：`f3be40026a352dd279691ed7f1dc99665f997be6b367a3f7614e2d32555496db`；
- used for official OOF：false。

## 7. Environment

- Python 3.13.1
- scikit-learn 1.9.0
- NumPy 2.5.1
- joblib 1.5.3

## 8. Limitations

- 标签来自星级规则，不是人工真值；
- 类别明显不均衡；
- neutral 识别较弱；
- 10 个拟合阶段达到 `max_iter=1000`，ConvergenceWarning 已记录；
- 模型是经典文本基线，不是 Transformer 或 LLM；
- OOF 是同一数据范围的交叉验证预测，不替代未来时间段或外部数据评估。

## 9. Result

NLP BASELINE TRAINING RESULT: PASS

HELD-OUT TEST EVALUATION RESULT: PASS

OOF PREDICTION GENERATION RESULT: PASS

PREDICTION CONTRACT VALIDATION RESULT: PASS

FULL MODEL ARTIFACT RESULT: PASS
