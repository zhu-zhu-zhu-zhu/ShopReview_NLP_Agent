"""Validate production NLP predictions without exposing review text."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable

LABELS = ("negative", "neutral", "positive")
PREDICTION_FIELDS = (
    "review_key",
    "pred_label",
    "pred_score",
    "negative_score",
    "neutral_score",
    "positive_score",
    "model_version",
    "inferred_at",
)
FORBIDDEN_FIELDS = {"review_text", "review_text_clean", "rating_label", "user_id"}


class PredictionValidationError(ValueError):
    """Raised when a prediction file violates the production contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
        return True
    except ValueError:
        return False


def _read_source_keys(input_path: Path) -> set[str]:
    keys: set[str] = set()
    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise PredictionValidationError(f"blank source line: {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PredictionValidationError(f"malformed source JSON: {line_number}") from exc
            key = row.get("review_key")
            if not isinstance(key, str) or not key:
                raise PredictionValidationError(f"blank source review_key: {line_number}")
            if key in keys:
                raise PredictionValidationError(f"duplicate source review_key: {line_number}")
            keys.add(key)
    return keys


def validate_predictions(
    input_path: Path,
    prediction_path: Path,
    expected_model_version: str,
    expected_row_count: int,
    probability_tolerance: float = 1e-5,
) -> dict[str, Any]:
    if not prediction_path.is_file():
        raise PredictionValidationError(f"prediction file not found: {prediction_path}")
    source_keys = _read_source_keys(input_path)
    if len(source_keys) != expected_row_count:
        raise PredictionValidationError(
            f"source row count mismatch: {len(source_keys)} != {expected_row_count}"
        )

    seen: set[str] = set()
    label_counts: Counter[str] = Counter()
    scores: list[float] = []
    inferred_values: set[str] = set()
    row_count = 0

    with prediction_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row_count += 1
            if not line.strip():
                raise PredictionValidationError(f"blank prediction line: {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PredictionValidationError(f"malformed prediction JSON: {line_number}") from exc
            if not isinstance(row, dict) or tuple(row) != PREDICTION_FIELDS:
                raise PredictionValidationError(f"invalid prediction field order: {line_number}")
            forbidden = FORBIDDEN_FIELDS.intersection(row)
            if forbidden:
                raise PredictionValidationError(
                    f"forbidden prediction fields at line {line_number}: {sorted(forbidden)}"
                )
            key = row["review_key"]
            if not isinstance(key, str) or not key:
                raise PredictionValidationError(f"blank prediction review_key: {line_number}")
            if key in seen:
                raise PredictionValidationError(f"duplicate prediction review_key: {line_number}")
            if key not in source_keys:
                raise PredictionValidationError(f"unknown prediction review_key: {line_number}")
            seen.add(key)

            label = row["pred_label"]
            if label not in LABELS:
                raise PredictionValidationError(f"invalid pred_label: {line_number}")
            if row["model_version"] != expected_model_version:
                raise PredictionValidationError(f"invalid model_version: {line_number}")
            if not _parse_utc(row["inferred_at"]):
                raise PredictionValidationError(f"invalid inferred_at: {line_number}")
            inferred_values.add(row["inferred_at"])

            class_scores: dict[str, float] = {}
            for class_name in LABELS:
                value = row[f"{class_name}_score"]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise PredictionValidationError(f"non-numeric class score: {line_number}")
                value = float(value)
                if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                    raise PredictionValidationError(f"class score outside [0,1]: {line_number}")
                class_scores[class_name] = value
            if abs(sum(class_scores.values()) - 1.0) > probability_tolerance:
                raise PredictionValidationError(f"probability sum mismatch: {line_number}")
            pred_score = row["pred_score"]
            if isinstance(pred_score, bool) or not isinstance(pred_score, (int, float)):
                raise PredictionValidationError(f"non-numeric pred_score: {line_number}")
            pred_score = float(pred_score)
            if not 0.0 <= pred_score <= 1.0:
                raise PredictionValidationError(f"pred_score outside [0,1]: {line_number}")
            if abs(pred_score - class_scores[label]) > probability_tolerance:
                raise PredictionValidationError(f"pred_score mismatch: {line_number}")
            scores.append(pred_score)
            label_counts[label] += 1

    missing = source_keys - seen
    if row_count != expected_row_count:
        raise PredictionValidationError(
            f"prediction row count mismatch: {row_count} != {expected_row_count}"
        )
    if missing:
        raise PredictionValidationError(f"missing prediction keys: {len(missing)}")
    if len(inferred_values) != 1:
        raise PredictionValidationError("inferred_at must be consistent across the run")

    return {
        "result": "PASS",
        "prediction_row_count": row_count,
        "unique_key_count": len(seen),
        "missing_key_count": 0,
        "unknown_key_count": 0,
        "duplicate_key_count": 0,
        "label_distribution": {label: label_counts[label] for label in LABELS},
        "pred_score": {
            "min": min(scores),
            "max": max(scores),
            "mean": fmean(scores),
        },
        "model_version": expected_model_version,
        "coverage": len(seen) / len(source_keys),
        "prediction_file_size_bytes": prediction_path.stat().st_size,
        "prediction_file_sha256": sha256_file(prediction_path),
        "inferred_at": next(iter(inferred_values)),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", type=Path, required=True)
    parser.add_argument("--prediction-path", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    parser.add_argument("--expected-model-version", default="tfidf_logreg_v1")
    parser.add_argument("--expected-row-count", type=int, default=99703)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = validate_predictions(
        args.input_path,
        args.prediction_path,
        args.expected_model_version,
        args.expected_row_count,
    )
    write_json_atomic(args.output_summary, summary)
    print(
        f"PredictionRows={summary['prediction_row_count']} "
        f"Coverage={summary['coverage']:.6f} Result=PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
