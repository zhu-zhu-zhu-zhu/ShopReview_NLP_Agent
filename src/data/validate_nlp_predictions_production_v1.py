#!/usr/bin/env python3
"""Validate real production-v1 NLP predictions without loading them into memory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
from collections import Counter
from collections.abc import Iterable, Iterator
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_BATCH_ID = "prod_v1_100k"
SOURCE_TABLE = "review_dw.dwd_amazon_fashion_review"
VALID_LABELS = {"negative", "neutral", "positive"}
REQUIRED_FIELDS = {"review_key", "pred_label", "pred_score", "model_version", "inferred_at"}
OPTIONAL_FIELDS = {"negative_score", "neutral_score", "positive_score"}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
FORBIDDEN_FIELDS = {
    "user_id", "review_text", "review_text_clean", "api_key", "apikey",
    "credentials", "credential", "password", "sql", "query",
}
MODEL_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DWD_KEY_RE = re.compile(r"^[0-9a-f]{64}$")
BEELINE_PROMPT = re.compile(r"^\d+: jdbc:hive2://[^>]+> ")
CONTROL_CHARS = ("\x01", "\r", "\n", "\t")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate[:-1] + "+00:00" if candidate.endswith("Z") else candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed.astimezone(timezone.utc)


def model_version_partition(model_version: str) -> str:
    if not MODEL_VERSION_RE.fullmatch(model_version):
        raise ValueError("model_version must use only letters, digits, dot, underscore, or hyphen")
    normalized = re.sub(r"[^a-z0-9_-]+", "_", model_version.lower()).strip("_") or "model"
    digest = hashlib.sha256(model_version.encode("utf-8")).hexdigest()[:12]
    return f"{normalized[:80]}_{digest}"


def record_errors(record: Any, expected_model_version: str) -> set[str]:
    errors: set[str] = set()
    if not isinstance(record, dict):
        return {"non_object"}
    field_names = set(record)
    if REQUIRED_FIELDS - field_names:
        errors.add("missing_required_field")
    lower_names = {str(name).lower() for name in field_names}
    if lower_names & FORBIDDEN_FIELDS:
        errors.add("forbidden_field")
    if field_names - ALLOWED_FIELDS:
        errors.add("unexpected_field")

    review_key = record.get("review_key")
    if not isinstance(review_key, str) or not review_key.strip():
        errors.add("invalid_review_key")
    elif any(character in review_key for character in CONTROL_CHARS):
        errors.add("invalid_review_key")

    if record.get("pred_label") not in VALID_LABELS:
        errors.add("invalid_label")

    score = record.get("pred_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= float(score) <= 1:
        errors.add("invalid_score")

    model_version = record.get("model_version")
    if not isinstance(model_version, str) or not model_version.strip():
        errors.add("blank_model_version")
    elif not MODEL_VERSION_RE.fullmatch(model_version):
        errors.add("unsafe_model_version")
    elif model_version != expected_model_version:
        errors.add("model_version_mismatch")

    if parse_utc_timestamp(record.get("inferred_at")) is None:
        errors.add("invalid_timestamp")

    for field in OPTIONAL_FIELDS:
        optional_score = record.get(field)
        if optional_score is not None and (
            isinstance(optional_score, bool)
            or not isinstance(optional_score, (int, float))
            or not 0 <= float(optional_score) <= 1
        ):
            errors.add("invalid_optional_score")
    return errors


def iter_hive_dwd_keys(container: str, jdbc: str, batch_id: str) -> Iterator[str]:
    if batch_id != DEFAULT_BATCH_ID:
        raise ValueError("production-v1 key validation only permits batch prod_v1_100k")
    query = (
        "SELECT review_key FROM review_dw.dwd_amazon_fashion_review "
        "WHERE load_batch_id='prod_v1_100k' AND review_key IS NOT NULL AND trim(review_key)<>''"
    )
    command = [
        "docker", "exec", container, "beeline", "-u", jdbc, "--silent=true",
        "--showHeader=false", "--outputformat=tsv2",
        "--hiveconf", "hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat",
        "-e", query,
    ]
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as error_log:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=error_log,
            text=True, encoding="utf-8", errors="strict",
        )
        assert process.stdout is not None
        try:
            for raw_line in process.stdout:
                key = BEELINE_PROMPT.sub("", raw_line.rstrip("\r\n"), count=1)
                if key:
                    if not DWD_KEY_RE.fullmatch(key):
                        raise ValueError("Hive DWD key query returned an invalid review_key")
                    yield key
        except Exception:
            process.kill()
            process.wait()
            raise
        return_code = process.wait()
        if return_code != 0:
            error_log.seek(0)
            raise RuntimeError(f"Hive DWD key query failed: {error_log.read().strip()}")


def _prepare_database(connection: sqlite3.Connection, keys: Iterable[str]) -> int:
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("DROP TABLE IF EXISTS dwd_keys")
    connection.execute("DROP TABLE IF EXISTS prediction_keys")
    connection.execute("CREATE TABLE dwd_keys (review_key TEXT PRIMARY KEY)")
    connection.execute(
        "CREATE TABLE prediction_keys ("
        "review_key TEXT NOT NULL, model_version TEXT NOT NULL, pred_label TEXT NOT NULL, "
        "pred_score REAL NOT NULL, PRIMARY KEY(review_key, model_version))"
    )
    count = 0
    batch: list[tuple[str]] = []
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("DWD key source contains an invalid key")
        batch.append((key,))
        if len(batch) >= 5000:
            connection.executemany("INSERT INTO dwd_keys(review_key) VALUES (?)", batch)
            count += len(batch)
            batch.clear()
    if batch:
        connection.executemany("INSERT INTO dwd_keys(review_key) VALUES (?)", batch)
        count += len(batch)
    connection.commit()
    return count


def _load_manifest(path: Path, expected_batch_id: str) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("NLP input manifest must be a JSON object")
    if manifest.get("batch_id") != expected_batch_id:
        raise ValueError("NLP input manifest batch does not match expected batch")
    if manifest.get("source_table") != SOURCE_TABLE:
        raise ValueError("NLP input manifest source table is invalid")
    if "review_key" not in manifest.get("field_order", []):
        raise ValueError("NLP input manifest does not declare review_key")
    return manifest


def validate_prediction_file(
    prediction_path: Path,
    manifest_path: Path,
    sqlite_path: Path,
    expected_batch_id: str,
    expected_model_version: str,
    allow_partial: bool = False,
    minimum_coverage: float = 1.0,
    known_keys: Iterable[str] | None = None,
    container: str = "tier4_stu_hiveserver2",
    jdbc: str = "jdbc:hive2://localhost:10000/default",
) -> dict[str, Any]:
    if expected_batch_id != DEFAULT_BATCH_ID:
        raise ValueError("expected batch must be prod_v1_100k")
    if not MODEL_VERSION_RE.fullmatch(expected_model_version):
        raise ValueError("expected model version is blank or unsafe")
    if not 0 <= minimum_coverage <= 1:
        raise ValueError("minimum coverage must be between 0 and 1")
    if not prediction_path.is_file():
        raise FileNotFoundError(f"prediction file not found: {prediction_path}")
    _load_manifest(manifest_path, expected_batch_id)

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    key_source = known_keys if known_keys is not None else iter_hive_dwd_keys(container, jdbc, expected_batch_id)
    error_counts: Counter[str] = Counter()
    physical_lines = 0
    prediction_rows = 0
    parsed_objects = 0
    valid_rows = 0
    duplicate_count = 0

    with closing(sqlite3.connect(sqlite_path)) as connection:
        dwd_key_count = _prepare_database(connection, key_source)
        if dwd_key_count == 0:
            raise ValueError("DWD key source is empty")
        with prediction_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                physical_lines += 1
                if not line.strip():
                    error_counts["blank_line"] += 1
                    continue
                prediction_rows += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    error_counts["malformed_json"] += 1
                    continue
                if isinstance(record, dict):
                    parsed_objects += 1
                errors = record_errors(record, expected_model_version)
                if errors:
                    error_counts.update(errors)
                    continue
                try:
                    connection.execute(
                        "INSERT INTO prediction_keys(review_key,model_version,pred_label,pred_score) VALUES (?,?,?,?)",
                        (
                            record["review_key"], record["model_version"],
                            record["pred_label"], float(record["pred_score"]),
                        ),
                    )
                    valid_rows += 1
                except sqlite3.IntegrityError:
                    duplicate_count += 1
                    error_counts["duplicate_key_model_version"] += 1
        connection.commit()

        unique_review_key_count = connection.execute(
            "SELECT COUNT(DISTINCT review_key) FROM prediction_keys"
        ).fetchone()[0]
        unknown_key_count = connection.execute(
            "SELECT COUNT(*) FROM prediction_keys p LEFT JOIN dwd_keys d ON p.review_key=d.review_key "
            "WHERE d.review_key IS NULL"
        ).fetchone()[0]
        matched_key_count = connection.execute(
            "SELECT COUNT(DISTINCT p.review_key) FROM prediction_keys p JOIN dwd_keys d ON p.review_key=d.review_key"
        ).fetchone()[0]
        missing_key_count = connection.execute(
            "SELECT COUNT(*) FROM dwd_keys d LEFT JOIN prediction_keys p ON d.review_key=p.review_key "
            "WHERE p.review_key IS NULL"
        ).fetchone()[0]
        label_distribution = {label: 0 for label in sorted(VALID_LABELS)}
        for label, count in connection.execute(
            "SELECT pred_label,COUNT(*) FROM prediction_keys GROUP BY pred_label ORDER BY pred_label"
        ):
            label_distribution[label] = count
        model_distribution = {
            version: count for version, count in connection.execute(
                "SELECT model_version,COUNT(*) FROM prediction_keys GROUP BY model_version ORDER BY model_version"
            )
        }
        score_minimum, score_maximum, score_mean = connection.execute(
            "SELECT MIN(pred_score),MAX(pred_score),AVG(pred_score) FROM prediction_keys"
        ).fetchone()

    coverage_rate = matched_key_count / dwd_key_count
    failure_reasons = sorted(name for name, count in error_counts.items() if count)
    if unknown_key_count:
        failure_reasons.append("unknown_review_key")
    if coverage_rate < minimum_coverage:
        failure_reasons.append("coverage_below_minimum")
    if not allow_partial and missing_key_count:
        failure_reasons.append("partial_file_not_allowed")
    validation_passed = not failure_reasons

    return {
        "validation_status": "PASS" if validation_passed else "FAIL",
        "validated_at": utc_now(),
        "batch_id": expected_batch_id,
        "source_table": SOURCE_TABLE,
        "expected_model_version": expected_model_version,
        "model_version_partition": model_version_partition(expected_model_version),
        "allow_partial": allow_partial,
        "minimum_coverage": minimum_coverage,
        "dwd_key_count": dwd_key_count,
        "physical_line_count": physical_lines,
        "prediction_row_count": prediction_rows,
        "parsed_object_count": parsed_objects,
        "valid_prediction_row_count": valid_rows,
        "unique_review_key_count": unique_review_key_count,
        "duplicate_count": duplicate_count,
        "unknown_key_count": unknown_key_count,
        "missing_key_count": missing_key_count,
        "matched_key_count": matched_key_count,
        "coverage_rate": coverage_rate,
        "label_distribution": label_distribution,
        "score_minimum": score_minimum,
        "score_maximum": score_maximum,
        "score_mean": score_mean,
        "model_version_distribution": model_distribution,
        "invalid_timestamp_count": error_counts["invalid_timestamp"],
        "malformed_json_count": error_counts["malformed_json"],
        "blank_line_count": error_counts["blank_line"],
        "missing_required_field_count": error_counts["missing_required_field"],
        "invalid_label_count": error_counts["invalid_label"],
        "invalid_score_count": error_counts["invalid_score"] + error_counts["invalid_optional_score"],
        "blank_model_version_count": error_counts["blank_model_version"],
        "model_version_mismatch_count": error_counts["model_version_mismatch"],
        "forbidden_field_count": error_counts["forbidden_field"],
        "unexpected_field_count": error_counts["unexpected_field"],
        "invalid_record_count": prediction_rows - valid_rows,
        "failure_reasons": sorted(set(failure_reasons)),
        "prediction_file_size_bytes": prediction_path.stat().st_size,
        "prediction_file_sha256": file_sha256(prediction_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction-path", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    parser.add_argument("--expected-batch-id", default=DEFAULT_BATCH_ID)
    parser.add_argument("--expected-model-version", required=True)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--minimum-coverage", type=float, default=1.0)
    parser.add_argument("--container", default="tier4_stu_hiveserver2")
    parser.add_argument("--jdbc", default="jdbc:hive2://localhost:10000/default")
    args = parser.parse_args()
    state_path = Path("data/state/nlp_predictions_production_v1") / f"{args.expected_batch_id}.sqlite"
    try:
        summary = validate_prediction_file(
            args.prediction_path, args.manifest_path, state_path,
            args.expected_batch_id, args.expected_model_version,
            allow_partial=args.allow_partial, minimum_coverage=args.minimum_coverage,
            container=args.container, jdbc=args.jdbc,
        )
        atomic_json(args.output_summary, summary)
        if summary["validation_status"] != "PASS":
            print(
                "PRODUCTION NLP PREDICTION VALIDATION: FAIL "
                f"rows={summary['prediction_row_count']} coverage={summary['coverage_rate']:.6f} "
                f"reasons={','.join(summary['failure_reasons'])}"
            )
            return 1
        print(
            "PRODUCTION NLP PREDICTION VALIDATION: PASS "
            f"rows={summary['prediction_row_count']} coverage={summary['coverage_rate']:.6f}"
        )
    except Exception as exc:
        print(f"PRODUCTION NLP PREDICTION VALIDATION: FAIL: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
