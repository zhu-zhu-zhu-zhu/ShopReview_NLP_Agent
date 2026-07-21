#!/usr/bin/env python3
"""Stream and validate the production-v1 NLP input export from Hive."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


SCHEMA_VERSION = "production_v1.0"
DEFAULT_BATCH_ID = "prod_v1_100k"
SOURCE_TABLE = "review_dw.dwd_amazon_fashion_review"
EXPORT_TABLE = "review_dw.tmp_nlp_input_prod_v1_100k"
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
VALID_LABELS = {"negative", "neutral", "positive"}
FORBIDDEN_FIELDS = {"user_id", "review_text", "raw_metadata", "api_key", "credential", "password"}
BEELINE_PROMPT = re.compile(r"^\d+: jdbc:hive2://[^>]+> ")
FIELD_MEANINGS = {
    "review_key": "Warehouse-generated stable identifier; preserve exactly.",
    "review_text_clean": "Cleaned non-empty review text for NLP input.",
    "rating_label": "Rating-derived weak label; not a model prediction.",
    "rating": "Original star rating.",
    "parent_asin": "Product-family identifier.",
    "main_category": "Product category when metadata matched.",
    "review_time": "Parsed review timestamp.",
    "load_batch_id": "Warehouse production batch identifier.",
}
EXPECTED_TYPES = {
    "review_key": "string",
    "review_text_clean": "string",
    "rating_label": "string enum: negative|neutral|positive",
    "rating": "number",
    "parent_asin": "string|null",
    "main_category": "string|null",
    "review_time": "string|null (Hive timestamp)",
    "load_batch_id": "string",
}


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


def validate_record(record: Any, batch_id: str) -> None:
    if not isinstance(record, dict):
        raise ValueError("export row must be a JSON object")
    if tuple(record) != EXPECTED_FIELDS:
        raise ValueError("export row fields or deterministic field order are invalid")
    forbidden = FORBIDDEN_FIELDS.intersection(record)
    if forbidden:
        raise ValueError(f"forbidden export field(s): {', '.join(sorted(forbidden))}")
    key = record["review_key"]
    if not isinstance(key, str) or not key.strip():
        raise ValueError("review_key is required and non-blank")
    text = record["review_text_clean"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("review_text_clean is required and non-blank")
    if record["rating_label"] not in VALID_LABELS:
        raise ValueError("rating_label is invalid")
    rating = record["rating"]
    if isinstance(rating, bool) or not isinstance(rating, (int, float)):
        raise ValueError("rating must be numeric")
    if not 1 <= float(rating) <= 5:
        raise ValueError("rating must be between 1 and 5")
    for field in ("parent_asin", "main_category", "review_time"):
        if record[field] is not None and not isinstance(record[field], str):
            raise ValueError(f"{field} must be a string or null")
    if record["load_batch_id"] != batch_id:
        raise ValueError("load_batch_id does not match the requested batch")


def _decode_hive_string(value: str) -> str | None:
    if value == "~":
        return None
    try:
        return base64.b64decode(value, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid Base64 UTF-8 field from Hive") from exc


def _hive_export_query(batch_id: str) -> str:
    if batch_id != DEFAULT_BATCH_ID:
        raise ValueError("production-v1 export only permits batch prod_v1_100k")
    encoded = (
        "CASE WHEN review_key IS NULL THEN '~' ELSE base64(encode(review_key,'UTF-8')) END AS encoded_review_key",
        "CASE WHEN review_text_clean IS NULL THEN '~' ELSE base64(encode(review_text_clean,'UTF-8')) END AS encoded_review_text",
        "CASE WHEN rating_label IS NULL THEN '~' ELSE base64(encode(rating_label,'UTF-8')) END AS encoded_rating_label",
        "CASE WHEN rating IS NULL THEN '~' ELSE CAST(rating AS STRING) END AS encoded_rating",
        "CASE WHEN parent_asin IS NULL THEN '~' ELSE base64(encode(parent_asin,'UTF-8')) END AS encoded_parent_asin",
        "CASE WHEN main_category IS NULL THEN '~' ELSE base64(encode(main_category,'UTF-8')) END AS encoded_main_category",
        "CASE WHEN review_time IS NULL THEN '~' ELSE base64(encode(CAST(review_time AS STRING),'UTF-8')) END AS encoded_review_time",
        "CASE WHEN load_batch_id IS NULL THEN '~' ELSE base64(encode(load_batch_id,'UTF-8')) END AS encoded_batch_id",
    )
    return f"SELECT {','.join(encoded)} FROM {EXPORT_TABLE} ORDER BY encoded_review_key"


def hive_records(container: str, jdbc: str, batch_id: str) -> Iterator[dict[str, Any]]:
    command = [
        "docker", "exec", container, "beeline", "-u", jdbc, "--silent=true",
        "--showHeader=false", "--outputformat=tsv2",
        "--hiveconf", "hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat",
        "--hiveconf", "hive.merge.mapfiles=false",
        "--hiveconf", "hive.merge.mapredfiles=false",
        "--hiveconf", "hive.merge.tezfiles=false",
        "-e", _hive_export_query(batch_id),
    ]
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as error_log:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=error_log,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
        assert process.stdout is not None
        try:
            for line_number, raw_line in enumerate(process.stdout, start=1):
                line = raw_line.rstrip("\r\n")
                if not line:
                    continue
                values = line.split("\t")
                if len(values) != len(EXPECTED_FIELDS):
                    raise ValueError(
                        f"Hive export row {line_number}: expected 8 columns, got {len(values)}"
                    )
                values[0] = BEELINE_PROMPT.sub("", values[0], count=1)
                decoded = [_decode_hive_string(value) for value in values[:3]]
                rating = None if values[3] == "~" else float(values[3])
                decoded.extend(_decode_hive_string(value) for value in values[4:])
                record_values = (
                    decoded[0], decoded[1], decoded[2], rating,
                    decoded[3], decoded[4], decoded[5], decoded[6],
                )
                yield dict(zip(EXPECTED_FIELDS, record_values))
        except Exception:
            process.kill()
            process.wait()
            raise
        return_code = process.wait()
        if return_code != 0:
            error_log.seek(0)
            raise RuntimeError(f"Hive export query failed: {error_log.read().strip()}")


def _new_metrics() -> dict[str, Any]:
    return {
        "export_row_count": 0,
        "unique_review_key_count": 0,
        "duplicate_review_key_count": 0,
        "null_review_key_count": 0,
        "blank_review_text_count": 0,
        "invalid_rating_label_count": 0,
        "negative_count": 0,
        "neutral_count": 0,
        "positive_count": 0,
        "minimum_rating": None,
        "maximum_rating": None,
        "rows_with_parent_asin": 0,
        "rows_with_main_category": 0,
        "rows_with_review_time": 0,
    }


def _update_metrics(metrics: dict[str, Any], record: dict[str, Any], seen_keys: set[str]) -> None:
    metrics["export_row_count"] += 1
    key = record.get("review_key")
    if key is None or not isinstance(key, str) or not key.strip():
        metrics["null_review_key_count"] += 1
    elif key in seen_keys:
        metrics["duplicate_review_key_count"] += 1
    else:
        seen_keys.add(key)
        metrics["unique_review_key_count"] += 1
    text = record.get("review_text_clean")
    if not isinstance(text, str) or not text.strip():
        metrics["blank_review_text_count"] += 1
    label = record.get("rating_label")
    if label in VALID_LABELS:
        metrics[f"{label}_count"] += 1
    else:
        metrics["invalid_rating_label_count"] += 1
    rating = record.get("rating")
    if isinstance(rating, (int, float)) and not isinstance(rating, bool):
        value = float(rating)
        metrics["minimum_rating"] = value if metrics["minimum_rating"] is None else min(metrics["minimum_rating"], value)
        metrics["maximum_rating"] = value if metrics["maximum_rating"] is None else max(metrics["maximum_rating"], value)
    for field, metric in (
        ("parent_asin", "rows_with_parent_asin"),
        ("main_category", "rows_with_main_category"),
        ("review_time", "rows_with_review_time"),
    ):
        if record.get(field) is not None and str(record[field]).strip():
            metrics[metric] += 1


def _assert_reconciliation(metrics: dict[str, Any]) -> None:
    rows = metrics["export_row_count"]
    if metrics["unique_review_key_count"] + metrics["duplicate_review_key_count"] + metrics["null_review_key_count"] != rows:
        raise ValueError("review-key metrics do not reconcile to export rows")
    if metrics["negative_count"] + metrics["neutral_count"] + metrics["positive_count"] + metrics["invalid_rating_label_count"] != rows:
        raise ValueError("label metrics do not reconcile to export rows")
    for name in (
        "duplicate_review_key_count", "null_review_key_count",
        "blank_review_text_count", "invalid_rating_label_count",
    ):
        if metrics[name] != 0:
            raise ValueError(f"quality invariant failed: {name}={metrics[name]}")


def _summary_payload(
    metrics: dict[str, Any], output_path: Path, batch_id: str, source_table: str,
    export_timestamp: str,
) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "source_table": source_table,
        **metrics,
        "export_timestamp": export_timestamp,
        "schema_version": SCHEMA_VERSION,
        "output_filename": output_path.name,
        "output_file_size_bytes": output_path.stat().st_size,
        "output_file_sha256": file_sha256(output_path),
    }


def _manifest_payload(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "field_order": list(EXPECTED_FIELDS),
        "field_meanings": FIELD_MEANINGS,
        "expected_types": EXPECTED_TYPES,
        "batch_id": summary["batch_id"],
        "source_table": summary["source_table"],
        "label_mapping": {
            "rating_1_to_2": "negative",
            "rating_3": "neutral",
            "rating_4_to_5": "positive",
        },
        "rating_label_is_weak_label": True,
        "rating_label_statement": "rating_label is derived from star rating and is not an NLP model prediction.",
        "output_filename": summary["output_filename"],
        "output_file_sha256": summary["output_file_sha256"],
        "generated_timestamp": summary["export_timestamp"],
    }


def write_export(
    records: Iterable[dict[str, Any]], output_path: Path, summary_path: Path,
    manifest_path: Path, batch_id: str = DEFAULT_BATCH_ID,
    source_table: str = SOURCE_TABLE, generated_at_utc: str | None = None,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent)
    metrics = _new_metrics()
    seen_keys: set[str] = set()
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                _update_metrics(metrics, record, seen_keys)
                validate_record(record, batch_id)
                if metrics["duplicate_review_key_count"]:
                    raise ValueError(f"duplicate review_key detected: {record['review_key']}")
                json.dump(record, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
                handle.write("\n")
            _assert_reconciliation(metrics)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    timestamp = generated_at_utc or utc_now()
    summary = _summary_payload(metrics, output_path, batch_id, source_table, timestamp)
    manifest = _manifest_payload(summary)
    atomic_json(summary_path, summary)
    atomic_json(manifest_path, manifest)
    return summary


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if FORBIDDEN_FIELDS.intersection(value):
        raise ValueError(f"{path} contains a forbidden field")
    return value


def profile_existing(path: Path, batch_id: str) -> dict[str, Any]:
    metrics = _new_metrics()
    seen_keys: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"blank JSONL line at {line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed JSONL line at {line_number}") from exc
            _update_metrics(metrics, record, seen_keys)
            validate_record(record, batch_id)
    _assert_reconciliation(metrics)
    return metrics


def validate_existing(
    output_path: Path, summary_path: Path, manifest_path: Path,
    batch_id: str = DEFAULT_BATCH_ID, expected_row_count: int | None = None,
) -> dict[str, Any]:
    if not output_path.is_file() or not summary_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("export, summary, or manifest is missing")
    metrics = profile_existing(output_path, batch_id)
    if expected_row_count is not None and metrics["export_row_count"] != expected_row_count:
        raise ValueError("local export row count does not match Hive eligible row count")
    summary = _load_json_object(summary_path)
    manifest = _load_json_object(manifest_path)
    expected_summary = _summary_payload(
        metrics, output_path, batch_id, SOURCE_TABLE, summary.get("export_timestamp", ""),
    )
    if summary != expected_summary:
        raise ValueError("summary does not reconcile to the local export")
    if manifest != _manifest_payload(summary):
        raise ValueError("manifest does not reconcile to the summary or export hash")
    return summary


def sanitized_previews(path: Path, limit: int = 3) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            previews.append({
                "review_key_prefix": record["review_key"][:12],
                "rating_label": record["rating_label"],
                "rating": record["rating"],
                "parent_asin": record["parent_asin"],
                "main_category": record["main_category"],
                "review_text_length": len(record["review_text_clean"]),
            })
            if len(previews) >= limit:
                break
    return previews


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="tier4_stu_hiveserver2")
    parser.add_argument("--jdbc", default="jdbc:hive2://localhost:10000/default")
    parser.add_argument("--batch-id", default=DEFAULT_BATCH_ID)
    parser.add_argument("--output-path", type=Path, default=Path("data/processed/nlp_production_v1/nlp_input_prod_v1.jsonl"))
    parser.add_argument("--summary-path", type=Path, default=Path("reports/nlp_handoff/nlp_input_prod_v1_summary.json"))
    parser.add_argument("--manifest-path", type=Path, default=Path("reports/nlp_handoff/nlp_input_prod_v1_manifest.json"))
    parser.add_argument("--expected-row-count", type=int)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.batch_id != DEFAULT_BATCH_ID:
            raise ValueError("production-v1 export only permits batch prod_v1_100k")
        if args.validate_only:
            summary = validate_existing(
                args.output_path, args.summary_path, args.manifest_path,
                batch_id=args.batch_id, expected_row_count=args.expected_row_count,
            )
            print(f"NLP INPUT LOCAL VALIDATION: PASS rows={summary['export_row_count']}")
        else:
            summary = write_export(
                hive_records(args.container, args.jdbc, args.batch_id),
                args.output_path, args.summary_path, args.manifest_path,
                batch_id=args.batch_id,
            )
            print(f"NLP INPUT EXPORT: PASS rows={summary['export_row_count']}")
        for preview in sanitized_previews(args.output_path):
            print(json.dumps(preview, ensure_ascii=False, separators=(",", ":")))
    except Exception as exc:
        print(f"NLP INPUT EXPORT: FAIL: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
