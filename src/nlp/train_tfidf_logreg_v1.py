"""Train, evaluate and run the production-v1 TF-IDF sentiment baseline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import joblib
import matplotlib
import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

from src.nlp.validate_prediction_output import (
    LABELS,
    validate_predictions,
    write_json_atomic,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

EXPECTED_FIELDS = (
    "review_key",
    "review_text_clean",
    "rating_label",
    "rating",
    "parent_asin",
    "main_category",
    "review_time",
    "load_batch_id",
)
EXPECTED_BATCH_ID = "prod_v1_100k"
C_CANDIDATES = (0.5, 1.0, 2.0)


class InputValidationError(ValueError):
    """Raised when the production input violates its contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_input_jsonl(
    path: Path,
    expected_sha256: str,
    expected_row_count: int,
    expected_batch_id: str = EXPECTED_BATCH_ID,
) -> tuple[list[str], list[str], list[str], dict[str, Any]]:
    if not path.is_file():
        raise InputValidationError(f"input file not found: {path}")
    actual_sha256 = sha256_file(path)
    if actual_sha256.lower() != expected_sha256.lower():
        raise InputValidationError(
            f"input SHA-256 mismatch: {actual_sha256} != {expected_sha256}"
        )

    keys: list[str] = []
    texts: list[str] = []
    labels: list[str] = []
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise InputValidationError(f"blank input line: {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputValidationError(f"malformed input JSON: {line_number}") from exc
            if not isinstance(row, dict) or tuple(row) != EXPECTED_FIELDS:
                raise InputValidationError(f"unexpected input fields/order: {line_number}")
            if "user_id" in row:
                raise InputValidationError(f"forbidden user_id field: {line_number}")
            key = row["review_key"]
            if not isinstance(key, str) or not key:
                raise InputValidationError(f"blank review_key: {line_number}")
            if key in seen:
                raise InputValidationError(f"duplicate review_key: {line_number}")
            text = row["review_text_clean"]
            if not isinstance(text, str) or not text.strip():
                raise InputValidationError(f"blank review_text_clean: {line_number}")
            label = row["rating_label"]
            if label not in LABELS:
                raise InputValidationError(f"invalid rating_label: {line_number}")
            if row["load_batch_id"] != expected_batch_id:
                raise InputValidationError(f"unexpected load_batch_id: {line_number}")
            seen.add(key)
            keys.append(key)
            texts.append(text)
            labels.append(label)
            counts[label] += 1
    if len(keys) != expected_row_count:
        raise InputValidationError(
            f"input row count mismatch: {len(keys)} != {expected_row_count}"
        )
    profile = {
        "row_count": len(keys),
        "unique_key_count": len(seen),
        "label_distribution": {label: counts[label] for label in LABELS},
        "input_sha256": actual_sha256,
        "batch_id": expected_batch_id,
    }
    return keys, texts, labels, profile


def stratified_split_indices(
    labels: Sequence[str], random_state: int
) -> tuple[list[int], list[int], list[int]]:
    indices = list(range(len(labels)))
    train_idx, temporary_idx = train_test_split(
        indices,
        test_size=0.20,
        random_state=random_state,
        stratify=list(labels),
    )
    temporary_labels = [labels[index] for index in temporary_idx]
    validation_idx, test_idx = train_test_split(
        temporary_idx,
        test_size=0.50,
        random_state=random_state,
        stratify=temporary_labels,
    )
    return list(train_idx), list(validation_idx), list(test_idx)


def split_statistics(indices: Sequence[int], labels: Sequence[str]) -> dict[str, Any]:
    counts = Counter(labels[index] for index in indices)
    total = len(indices)
    return {
        "row_count": total,
        "label_counts": {label: counts[label] for label in LABELS},
        "label_percentages": {
            label: (counts[label] / total if total else 0.0) for label in LABELS
        },
    }


def build_pipeline(
    c_value: float,
    random_state: int,
    max_features: int,
    min_df: int,
    max_df: float,
    ngram_max: int,
    max_iter: int,
) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, ngram_max),
                    max_features=max_features,
                    min_df=min_df,
                    max_df=max_df,
                    sublinear_tf=True,
                    dtype=np.float32,
                ),
            ),
            (
                "logistic_regression",
                LogisticRegression(
                    C=c_value,
                    class_weight="balanced",
                    random_state=random_state,
                    solver="saga",
                    max_iter=max_iter,
                    tol=1e-4,
                ),
            ),
        ]
    )


def fit_with_warning_capture(model: Pipeline, texts: Sequence[str], labels: Sequence[str]) -> list[str]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(texts, labels)
    return [str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning)]


def basic_metrics(labels: Sequence[str], predictions: Sequence[str]) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(labels, predictions, average="macro", zero_division=0)),
        "weighted_f1": float(
            f1_score(labels, predictions, average="weighted", zero_division=0)
        ),
    }


def test_metrics(labels: Sequence[str], predictions: Sequence[str]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predictions, labels=list(LABELS), zero_division=0
    )
    macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
        labels, predictions, average="macro", zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_precision": float(macro_precision),
        "macro_recall": float(macro_recall),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(
            f1_score(labels, predictions, average="weighted", zero_division=0)
        ),
        "per_class": {
            label: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, label in enumerate(LABELS)
        },
    }


def _write_csv(path: Path, rows: Iterable[Sequence[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)
    os.replace(temporary, path)


def write_classification_csv(path: Path, metrics: dict[str, Any]) -> None:
    rows: list[Sequence[Any]] = [("class", "precision", "recall", "f1", "support")]
    for label in LABELS:
        item = metrics["per_class"][label]
        rows.append((label, item["precision"], item["recall"], item["f1"], item["support"]))
    _write_csv(path, rows)


def write_matrix_csv(path: Path, matrix: np.ndarray) -> None:
    rows: list[Sequence[Any]] = [("actual\\predicted", *LABELS)]
    for index, label in enumerate(LABELS):
        rows.append((label, *matrix[index].tolist()))
    _write_csv(path, rows)


def write_confusion_figure(path: Path, matrix: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7, 6))
    image = axis.imshow(matrix, interpolation="nearest", cmap="Blues", vmin=0.0, vmax=1.0)
    figure.colorbar(image, ax=axis)
    axis.set(
        xticks=np.arange(len(LABELS)),
        yticks=np.arange(len(LABELS)),
        xticklabels=LABELS,
        yticklabels=LABELS,
        xlabel="Predicted label",
        ylabel="True label",
        title="TF-IDF + Logistic Regression (normalized)",
    )
    for row in range(len(LABELS)):
        for column in range(len(LABELS)):
            axis.text(column, row, f"{matrix[row, column]:.3f}", ha="center", va="center")
    figure.tight_layout()
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def generate_oof_predictions(
    path: Path,
    keys: Sequence[str],
    texts: Sequence[str],
    labels: Sequence[str],
    selected_c: float,
    model_version: str,
    inferred_at: str,
    random_state: int,
    max_features: int,
    min_df: int,
    max_df: float,
    ngram_max: int,
    max_iter: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Create one prediction per row from a fold model that never saw that row."""
    row_count = len(texts)
    oof_labels: list[str | None] = [None] * row_count
    oof_probabilities = np.full((row_count, len(LABELS)), np.nan, dtype=np.float64)
    fold_statistics: list[dict[str, Any]] = []
    convergence_warnings: list[dict[str, Any]] = []
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)

    for fold_number, (fold_train, fold_holdout) in enumerate(
        splitter.split(np.zeros(row_count), labels), 1
    ):
        fold_model = build_pipeline(
            selected_c,
            random_state,
            max_features,
            min_df,
            max_df,
            ngram_max,
            max_iter,
        )
        warnings_for_fold = fit_with_warning_capture(
            fold_model,
            [texts[index] for index in fold_train],
            [labels[index] for index in fold_train],
        )
        holdout_texts = [texts[index] for index in fold_holdout]
        predictions = fold_model.predict(holdout_texts)
        probabilities = fold_model.predict_proba(holdout_texts)
        class_indexes = {name: list(fold_model.classes_).index(name) for name in LABELS}
        for offset, original_index in enumerate(fold_holdout):
            oof_labels[int(original_index)] = str(predictions[offset])
            for class_position, class_name in enumerate(LABELS):
                oof_probabilities[int(original_index), class_position] = float(
                    probabilities[offset, class_indexes[class_name]]
                )
        fold_statistics.append(
            {
                "fold": fold_number,
                "training_rows": int(len(fold_train)),
                "holdout_rows": int(len(fold_holdout)),
            }
        )
        if warnings_for_fold:
            convergence_warnings.append(
                {"stage": f"oof_fold_{fold_number}", "messages": warnings_for_fold}
            )

    if any(label is None for label in oof_labels) or np.isnan(oof_probabilities).any():
        raise RuntimeError("OOF prediction coverage is incomplete")

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for index, predicted_label_value in enumerate(oof_labels):
            predicted_label = str(predicted_label_value)
            class_scores = {
                class_name: float(oof_probabilities[index, class_position])
                for class_position, class_name in enumerate(LABELS)
            }
            row = {
                "review_key": keys[index],
                "pred_label": predicted_label,
                "pred_score": class_scores[predicted_label],
                "negative_score": class_scores["negative"],
                "neutral_score": class_scores["neutral"],
                "positive_score": class_scores["positive"],
                "model_version": model_version,
                "inferred_at": inferred_at,
            }
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, path)
    measured = basic_metrics(labels, [str(label) for label in oof_labels])
    return {
        "method": "5-fold Stratified Out-of-Fold",
        "n_splits": 5,
        "shuffle": True,
        "random_state": random_state,
        "source_row_used_in_own_fold_training": False,
        "folds": fold_statistics,
        "weak_label_comparison": measured,
    }, convergence_warnings


def write_report(
    path: Path,
    metrics: dict[str, Any],
    prediction_summary: dict[str, Any],
    model_manifest: dict[str, Any],
) -> None:
    split = metrics["split"]
    candidates = metrics["candidate_validation_results"]
    test = metrics["held_out_test"]
    lines = [
        "# Amazon Fashion 评论情感分类基线模型报告",
        "",
        "## 一、任务说明",
        "",
        "数据来自数仓 production-v1 的 99,703 条 Amazon Fashion 评论，目标为 negative、neutral、positive 三分类。`rating_label` 是由星级映射得到的弱监督训练目标，不是模型预测；模型特征仅使用 `review_text_clean`，未使用评分、商品或类目字段。",
        "",
        "## 二、数据划分",
        "",
        f"使用 random_state={metrics['random_state']} 按弱标签分层划分，训练/验证/测试分别为 {split['train']['row_count']}/{split['validation']['row_count']}/{split['test']['row_count']} 条。",
        "",
        "| 数据集 | negative | neutral | positive |",
        "|---|---:|---:|---:|",
    ]
    for name, label in (("train", "训练"), ("validation", "验证"), ("test", "测试")):
        counts = split[name]["label_counts"]
        lines.append(f"| {label} | {counts['negative']} | {counts['neutral']} | {counts['positive']} |")
    lines.extend(
        [
            "",
            "## 三、模型方法",
            "",
            "采用 unigram + bigram 的 TF-IDF 文本特征和带 `class_weight=balanced` 的 Logistic Regression。保留否定词，不使用英文停用词。由于类别不均衡，参数选择以各类别同权的 macro-F1 为主。",
            "",
            "## 四、参数选择",
            "",
            "| C | 验证 accuracy | 验证 macro-F1 | 验证 weighted-F1 |",
            "|---:|---:|---:|---:|",
        ]
    )
    for item in candidates:
        lines.append(
            f"| {item['C']} | {item['accuracy']:.6f} | {item['macro_f1']:.6f} | {item['weighted_f1']:.6f} |"
        )
    lines.extend(
        [
            "",
            f"按验证 macro-F1、再按 accuracy 决胜，选择 C={metrics['selected_C']}。",
            "",
            "## 五、测试集结果",
            "",
            f"留出测试集 accuracy={test['accuracy']:.6f}，macro-F1={test['macro_f1']:.6f}，weighted-F1={test['weighted_f1']:.6f}。测试集只在选定 C 并用训练集与验证集合并重训后评估一次。",
            "",
            "| 类别 | precision | recall | F1 | support |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for label in LABELS:
        item = test["per_class"][label]
        lines.append(
            f"| {label} | {item['precision']:.6f} | {item['recall']:.6f} | {item['f1']:.6f} | {item['support']} |"
        )
    lines.extend(
        [
            "",
            "归一化混淆矩阵：![归一化混淆矩阵](assets/nlp_tfidf_logreg_v1_confusion_matrix.png)",
            "",
            "## 六、5 折 OOF 官方预测与全量模型",
            "",
            f"数仓使用 5 折 Stratified OOF 预测（shuffle=True，random_state={metrics['random_state']}）。每条评论只由未训练过该记录的折模型预测，并按原始输入顺序回填。共生成 {prediction_summary['prediction_row_count']} 条 OOF 预测，唯一键 {prediction_summary['unique_key_count']} 个，覆盖率 {prediction_summary['coverage']:.2%}。预测标签分布为 {json.dumps(prediction_summary['label_distribution'], ensure_ascii=False)}，pred_score 范围为 {prediction_summary['pred_score']['min']:.6f}–{prediction_summary['pred_score']['max']:.6f}，输出 SHA-256 为 `{prediction_summary['prediction_file_sha256']}`。",
            "",
            f"在留出测试评估和 OOF 预测全部完成之后，另用全部 {model_manifest['training_row_count']} 条弱标注记录训练最终模型。该工件仅用于未来未见评论推理，没有参与本批官方 OOF 数仓预测。",
            "",
            "## 七、数仓交付格式",
            "",
            "预测 JSONL 固定包含：`review_key`、`pred_label`、`pred_score`、`negative_score`、`neutral_score`、`positive_score`、`model_version`、`inferred_at`。",
            "",
            "## 八、限制",
            "",
            "- 标签来自星级映射，属于弱监督标签，并非人工真值；",
            "- 本模型是经典机器学习基线，不是 Transformer 或大语言模型；",
            "- 三类分布不均衡，少数类结果需结合逐类指标理解；",
            f"- 本次共有 {len(metrics['convergence_warnings'])} 个拟合阶段在 max_iter=1000 达到迭代上限；相关 ConvergenceWarning 已完整记录在 metrics JSON，结果可作为基线，但后续应继续调优收敛性；",
            "- 官方数仓预测使用 5 折 OOF，每条记录均由未训练过该记录的折模型预测；",
            "- 最终全量模型仅供未来未见评论推理，没有用于生成本批官方数仓预测；",
            "- 本报告测试指标只来自未参与参数选择的独立留出测试集；",
            "- 当前未训练 Transformer 模型，也未执行数仓预测导入。",
            "",
            "## 九、结果",
            "",
            "训练、留出测试评估、5 折 OOF 预测、预测契约校验和未来推理全量模型工件均已通过。",
            "",
            "NLP BASELINE TRAINING RESULT: PASS",
            "",
            "HELD-OUT TEST EVALUATION RESULT: PASS",
            "",
            "OOF PREDICTION GENERATION RESULT: PASS",
            "",
            "PREDICTION CONTRACT VALIDATION RESULT: PASS",
            "",
            "FULL MODEL ARTIFACT RESULT: PASS",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-version", default="tfidf_logreg_v1")
    parser.add_argument("--prediction-model-version", default="tfidf_logreg_oof_v1")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-row-count", type=int, default=99703)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--max-features", type=int, default=50000)
    parser.add_argument("--min-df", type=int, default=2)
    parser.add_argument("--max-df", type=float, default=0.98)
    parser.add_argument("--ngram-max", type=int, default=2)
    parser.add_argument("--max-iter", type=int, default=1000)
    parser.add_argument("--skip-training", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    keys, texts, labels, input_profile = load_input_jsonl(
        args.input_path, args.expected_sha256, args.expected_row_count
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.model_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.model_dir / f"{args.model_version}.joblib"
    # The output directory is reports/nlp, so its grandparent is the worktree root.
    worktree_root = args.output_dir.parent.parent
    prediction_path = (
        worktree_root
        / "data"
        / "processed"
        / "nlp_predictions_production_v1"
        / f"predictions_{args.prediction_model_version}.jsonl"
    )
    metrics_path = args.output_dir / f"{args.model_version}_metrics.json"
    manifest_path = args.output_dir / f"{args.model_version}_model_manifest.json"
    summary_path = args.output_dir / f"{args.prediction_model_version}_prediction_summary.json"

    if args.skip_training:
        if not model_path.is_file():
            raise FileNotFoundError(f"existing model artifact required: {model_path}")
        if not metrics_path.is_file() or not manifest_path.is_file():
            raise FileNotFoundError("existing metrics and model manifest are required")
        prediction_summary = validate_predictions(
            args.input_path,
            prediction_path,
            args.prediction_model_version,
            args.expected_row_count,
        )
        print(
            f"ExistingModel=PASS Predictions={prediction_summary['prediction_row_count']} "
            f"Coverage={prediction_summary['coverage']:.6f}"
        )
        return 0

    train_idx, validation_idx, test_idx = stratified_split_indices(labels, args.random_state)
    train_texts = [texts[index] for index in train_idx]
    train_labels = [labels[index] for index in train_idx]
    validation_texts = [texts[index] for index in validation_idx]
    validation_labels = [labels[index] for index in validation_idx]

    candidate_results: list[dict[str, Any]] = []
    convergence_warnings: list[dict[str, Any]] = []
    for c_value in C_CANDIDATES:
        candidate = build_pipeline(
            c_value, args.random_state, args.max_features, args.min_df,
            args.max_df, args.ngram_max, args.max_iter
        )
        caught = fit_with_warning_capture(candidate, train_texts, train_labels)
        validation_predictions = candidate.predict(validation_texts)
        candidate_results.append(
            {"C": c_value, **basic_metrics(validation_labels, validation_predictions)}
        )
        if caught:
            convergence_warnings.append(
                {"stage": f"candidate_C_{c_value}", "messages": caught}
            )
    selected = max(
        candidate_results,
        key=lambda item: (item["macro_f1"], item["accuracy"], -item["C"]),
    )

    # The untouched test split is used exactly once, after C has been selected.
    train_validation_idx = train_idx + validation_idx
    evaluation_model = build_pipeline(
        selected["C"], args.random_state, args.max_features, args.min_df,
        args.max_df, args.ngram_max, args.max_iter
    )
    caught = fit_with_warning_capture(
        evaluation_model,
        [texts[index] for index in train_validation_idx],
        [labels[index] for index in train_validation_idx],
    )
    if caught:
        convergence_warnings.append({"stage": "train_plus_validation", "messages": caught})
    test_labels = [labels[index] for index in test_idx]
    test_predictions = evaluation_model.predict([texts[index] for index in test_idx])
    measured_test_metrics = test_metrics(test_labels, test_predictions)
    raw_matrix = confusion_matrix(test_labels, test_predictions, labels=list(LABELS))
    normalized_matrix = confusion_matrix(
        test_labels, test_predictions, labels=list(LABELS), normalize="true"
    )

    metrics = {
        "result": "PASS",
        "evaluation_model_version": args.model_version,
        "official_prediction_model_version": args.prediction_model_version,
        "input": input_profile,
        "random_state": args.random_state,
        "split": {
            "train": split_statistics(train_idx, labels),
            "validation": split_statistics(validation_idx, labels),
            "test": split_statistics(test_idx, labels),
        },
        "candidate_validation_results": candidate_results,
        "selection_rule": "highest validation macro_f1, then accuracy",
        "selected_C": selected["C"],
        "held_out_test": measured_test_metrics,
        "convergence_warnings": convergence_warnings,
        "package_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    write_classification_csv(
        args.output_dir / f"{args.model_version}_classification_report.csv",
        measured_test_metrics,
    )
    write_matrix_csv(
        args.output_dir / f"{args.model_version}_confusion_matrix.csv", raw_matrix
    )
    write_matrix_csv(
        args.output_dir / f"{args.model_version}_confusion_matrix_normalized.csv",
        normalized_matrix,
    )
    write_confusion_figure(
        worktree_root / "docs" / "assets" / f"nlp_{args.model_version}_confusion_matrix.png",
        normalized_matrix,
    )

    # Official warehouse predictions are OOF: no row is scored by a model trained on it.
    inferred_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    oof_details, oof_warnings = generate_oof_predictions(
        prediction_path, keys, texts, labels, selected["C"],
        args.prediction_model_version, inferred_at, args.random_state,
        args.max_features, args.min_df, args.max_df, args.ngram_max, args.max_iter,
    )
    metrics["oof_prediction"] = oof_details
    metrics["convergence_warnings"].extend(oof_warnings)
    prediction_summary = validate_predictions(
        args.input_path,
        prediction_path,
        args.prediction_model_version,
        args.expected_row_count,
    )
    metrics["oof_prediction"]["contract_validation"] = prediction_summary
    write_json_atomic(summary_path, prediction_summary)

    # This full-data model is only for future unseen reviews, never for the OOF file.
    final_model = build_pipeline(
        selected["C"], args.random_state, args.max_features, args.min_df,
        args.max_df, args.ngram_max, args.max_iter
    )
    caught = fit_with_warning_capture(final_model, texts, labels)
    if caught:
        metrics["convergence_warnings"].append(
            {"stage": "future_inference_full_data_model", "messages": caught}
        )
    temporary_model = model_path.with_suffix(model_path.suffix + ".tmp")
    joblib.dump(final_model, temporary_model)
    os.replace(temporary_model, model_path)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    manifest = {
            "result": "PASS",
            "model_version": args.model_version,
            "purpose": "future unseen-review inference only",
            "used_for_official_oof_predictions": False,
            "algorithm": "TfidfVectorizer + LogisticRegression",
            "feature_configuration": {
                "source_field": "review_text_clean",
                "lowercase": True,
                "strip_accents": "unicode",
                "ngram_range": [1, args.ngram_max],
                "max_features": args.max_features,
                "min_df": args.min_df,
                "max_df": args.max_df,
                "sublinear_tf": True,
                "dtype": "float32",
                "stop_words": None,
            },
            "selected_C": selected["C"],
            "class_weight": "balanced",
            "random_state": args.random_state,
            "training_row_count": len(labels),
            "label_distribution": input_profile["label_distribution"],
            "python_version": platform.python_version(),
            "scikit_learn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "input_sha256": input_profile["input_sha256"],
            "model_file_sha256": sha256_file(model_path),
            "generated_utc": generated_at,
    }
    write_json_atomic(manifest_path, manifest)
    metrics["full_data_model"] = {
        "purpose": manifest["purpose"],
        "training_row_count": len(labels),
        "model_file_sha256": manifest["model_file_sha256"],
        "used_for_official_oof_predictions": False,
    }
    write_json_atomic(metrics_path, metrics)
    write_report(
        worktree_root / "docs" / "NLP_BASELINE_TRAINING_REPORT.md",
        metrics,
        prediction_summary,
        manifest,
    )
    print(
        f"Rows={len(labels)} SelectedC={selected['C']} "
        f"OOFPredictions={prediction_summary['prediction_row_count']} "
        f"Coverage={prediction_summary['coverage']:.6f} FullModel=PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
