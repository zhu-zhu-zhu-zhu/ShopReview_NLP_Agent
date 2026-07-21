#!/usr/bin/env python3
"""Convert a validated production-v1 prediction JSONL file for Hive staging."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from src.data.prepare_ods_smoke_data import DELIMITER, NULL
from src.data.validate_nlp_predictions_production_v1 import (
    DEFAULT_BATCH_ID,
    atomic_json,
    model_version_partition,
    parse_utc_timestamp,
    record_errors,
    utc_now,
)


def _score(value: Any) -> str:
    return NULL if value is None else repr(float(value))


def prediction_columns(record: dict[str, Any], batch_id: str) -> list[str]:
    inferred_at = parse_utc_timestamp(record["inferred_at"])
    if inferred_at is None:
        raise ValueError("inferred_at must be a valid UTC timestamp")
    return [
        record["review_key"],
        record["pred_label"],
        _score(record["pred_score"]),
        _score(record.get("negative_score")),
        _score(record.get("neutral_score")),
        _score(record.get("positive_score")),
        record["model_version"],
        inferred_at.strftime("%Y-%m-%d %H:%M:%S"),
        batch_id,
    ]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def convert_predictions(
    prediction_path: Path,
    output_path: Path,
    summary_path: Path,
    batch_id: str,
    expected_model_version: str,
) -> dict[str, Any]:
    if batch_id != DEFAULT_BATCH_ID:
        raise ValueError("production-v1 conversion only permits batch prod_v1_100k")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent)
    row_count = 0
    labels: Counter[str] = Counter()
    seen_pairs: set[tuple[str, str]] = set()
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            with prediction_path.open("r", encoding="utf-8") as source:
                for line_number, line in enumerate(source, start=1):
                    if not line.strip():
                        raise ValueError(f"blank prediction line at {line_number}")
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"malformed prediction JSON at line {line_number}") from exc
                    errors = record_errors(record, expected_model_version)
                    if errors:
                        raise ValueError(f"invalid prediction record at line {line_number}: {','.join(sorted(errors))}")
                    pair = (record["review_key"], record["model_version"])
                    if pair in seen_pairs:
                        raise ValueError(f"duplicate prediction key/model at line {line_number}")
                    seen_pairs.add(pair)
                    columns = prediction_columns(record, batch_id)
                    if len(columns) != 9 or any(DELIMITER in value or "\n" in value or "\r" in value for value in columns):
                        raise ValueError(f"unsafe Hive field at line {line_number}")
                    output.write(DELIMITER.join(columns) + "\n")
                    row_count += 1
                    labels[record["pred_label"]] += 1
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, output_path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise

    summary = {
        "converted_at": utc_now(),
        "batch_id": batch_id,
        "model_version": expected_model_version,
        "model_version_partition": model_version_partition(expected_model_version),
        "converted_row_count": row_count,
        "column_count": 9,
        "label_distribution": {label: labels.get(label, 0) for label in ("negative", "neutral", "positive")},
        "output_filename": output_path.name,
        "output_file_size_bytes": output_path.stat().st_size,
        "output_file_sha256": _file_sha256(output_path),
    }
    atomic_json(summary_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    parser.add_argument("--batch-id", default=DEFAULT_BATCH_ID)
    parser.add_argument("--expected-model-version", required=True)
    args = parser.parse_args()
    try:
        summary = convert_predictions(
            args.prediction_path, args.output_path, args.output_summary,
            args.batch_id, args.expected_model_version,
        )
        print(f"NLP PREDICTION HIVE PREPARATION: PASS rows={summary['converted_row_count']}")
    except Exception as exc:
        print(f"NLP PREDICTION HIVE PREPARATION: FAIL: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
