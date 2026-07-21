#!/usr/bin/env python3
"""Export safe Phase F Hive DWS aggregates as Agent-readable JSON."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "draft_v0.1"
FORBIDDEN_FIELDS = {"user_id", "review_text", "review_text_clean", "api_key", "credential", "password"}
TABLE_SPECS = {
    "sentiment_overview": {
        "table": "review_dw.dws_sentiment_overview_smoke",
        "fields": (
            "review_count", "user_count", "product_count", "positive_count", "neutral_count",
            "negative_count", "positive_rate", "neutral_rate", "negative_rate", "average_rating",
            "generated_at", "data_scope",
        ),
        "integers": {"review_count", "user_count", "product_count", "positive_count", "neutral_count", "negative_count"},
        "floats": {"positive_rate", "neutral_rate", "negative_rate", "average_rating"},
        "order_by": "generated_at",
        "expected_scope": "phase_d_e_smoke_contract",
    },
    "product_sentiment": {
        "table": "review_dw.dws_product_sentiment_smoke",
        "fields": (
            "parent_asin", "product_title", "store_name", "review_count", "average_rating",
            "positive_count", "neutral_count", "negative_count", "positive_rate", "neutral_rate",
            "negative_rate", "verified_purchase_rate", "average_helpful_vote", "generated_at", "data_scope",
        ),
        "integers": {"review_count", "positive_count", "neutral_count", "negative_count"},
        "floats": {"average_rating", "positive_rate", "neutral_rate", "negative_rate", "verified_purchase_rate", "average_helpful_vote"},
        "order_by": "parent_asin, product_title, store_name",
        "expected_scope": "phase_d_e_smoke_contract",
    },
    "aspect_summary": {
        "table": "review_dw.dws_aspect_summary_smoke",
        "fields": (
            "aspect", "reason_code", "reason_name", "mention_count", "negative_count",
            "neutral_count", "positive_count", "negative_rate", "average_confidence",
            "extractor_version", "generated_at", "data_scope",
        ),
        "integers": {"mention_count", "negative_count", "neutral_count", "positive_count"},
        "floats": {"negative_rate", "average_confidence"},
        "order_by": "aspect, reason_code, reason_name, extractor_version",
        "expected_scope": "synthetic_aspect_contract_smoke",
    },
    "negative_reasons": {
        "table": "review_dw.dws_negative_reason_smoke",
        "fields": (
            "parent_asin", "product_title", "aspect", "reason_code", "reason_name",
            "reason_count", "reason_share", "extractor_version", "generated_at", "data_scope",
        ),
        "integers": {"reason_count"},
        "floats": {"reason_share"},
        "order_by": "parent_asin, aspect, reason_code, extractor_version",
        "expected_scope": "synthetic_aspect_contract_smoke",
    },
}


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


def _convert(value: str, field: str, integers: set[str], floats: set[str]) -> Any:
    if value in {"NULL", r"\N"}:
        return None
    if field in integers:
        return int(value)
    if field in floats:
        return float(value)
    return value


def query_records(container: str, jdbc: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
    fields = spec["fields"]
    sql = f"SELECT {','.join(fields)} FROM {spec['table']} ORDER BY {spec['order_by']};"
    command = [
        "docker", "exec", container, "beeline", "-u", jdbc, "--silent=true",
        "--showHeader=false", "--outputformat=tsv2", "-e", sql,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"Hive export query failed for {spec['table']}: {result.stderr.strip()}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(result.stdout.splitlines(), start=1):
        if not line.strip():
            continue
        values = line.split("\t")
        if len(values) != len(fields):
            raise ValueError(f"{spec['table']} row {line_number}: expected {len(fields)} columns, got {len(values)}")
        records.append({
            field: _convert(value, field, spec["integers"], spec["floats"])
            for field, value in zip(fields, values)
        })
    return records


def build_export_payload(name: str, spec: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset": name,
        "source_table": spec["table"],
        "data_scope": spec["expected_scope"],
        "records": records,
    }


def _walk_forbidden(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_FIELDS.intersection(value)
        if forbidden:
            raise ValueError(f"forbidden export field(s): {', '.join(sorted(forbidden))}")
        for child in value.values():
            _walk_forbidden(child)
    elif isinstance(value, list):
        for child in value:
            _walk_forbidden(child)


def validate_export_payload(payload: Any, expected_name: str, spec: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("export payload must be an object")
    if tuple(payload) != ("schema_version", "dataset", "source_table", "data_scope", "records"):
        raise ValueError("export wrapper fields or deterministic ordering are invalid")
    if payload["schema_version"] != SCHEMA_VERSION or payload["dataset"] != expected_name:
        raise ValueError("export identity is invalid")
    if payload["source_table"] != spec["table"] or payload["data_scope"] != spec["expected_scope"]:
        raise ValueError("export source or scope is invalid")
    if not isinstance(payload["records"], list):
        raise ValueError("records must be an array")
    expected_fields = tuple(spec["fields"])
    for index, record in enumerate(payload["records"], start=1):
        if not isinstance(record, dict) or tuple(record) != expected_fields:
            raise ValueError(f"record {index}: fields or deterministic ordering are invalid")
        if record["data_scope"] != spec["expected_scope"]:
            raise ValueError(f"record {index}: data_scope is invalid")
    _walk_forbidden(payload)


def export_all(container: str, jdbc: str, output_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, spec in TABLE_SPECS.items():
        records = query_records(container, jdbc, spec)
        payload = build_export_payload(name, spec, records)
        validate_export_payload(payload, name, spec)
        atomic_json(output_dir / f"{name}.json", payload)
        counts[name] = len(records)
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "export_name": "Phase F warehouse smoke",
        "purpose": "Agent mock-adapter development",
        "generated_at": generated_at,
        "sentiment_data": "Phase D/E contract smoke",
        "aspect_data": "synthetic contract data",
        "production_business_metrics": False,
        "tables": [spec["table"] for spec in TABLE_SPECS.values()],
        "files": [f"{name}.json" for name in TABLE_SPECS] + ["manifest.json"],
        "record_counts": counts,
    }
    _walk_forbidden(manifest)
    atomic_json(output_dir / "manifest.json", manifest)
    return counts


def validate_export_files(output_dir: Path) -> None:
    for name, spec in TABLE_SPECS.items():
        with (output_dir / f"{name}.json").open("r", encoding="utf-8") as handle:
            validate_export_payload(json.load(handle), name, spec)
    with (output_dir / "manifest.json").open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    required = {"schema_version", "export_name", "purpose", "generated_at", "sentiment_data", "aspect_data", "production_business_metrics", "tables", "files", "record_counts"}
    if set(manifest) != required or manifest["schema_version"] != SCHEMA_VERSION:
        raise ValueError("manifest schema is invalid")
    if manifest["production_business_metrics"] is not False:
        raise ValueError("manifest must label exports as non-production metrics")
    _walk_forbidden(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="tier4_stu_hiveserver2")
    parser.add_argument("--jdbc", default="jdbc:hive2://localhost:10000/default")
    parser.add_argument("--output-dir", type=Path, default=Path("exports/agent/smoke"))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_only:
            validate_export_files(args.output_dir)
            print("PHASE F AGENT JSON VALIDATION: PASS")
        else:
            counts = export_all(args.container, args.jdbc, args.output_dir)
            validate_export_files(args.output_dir)
            print("PHASE F AGENT JSON EXPORT: PASS: " + ", ".join(f"{name}={count}" for name, count in counts.items()))
    except Exception as exc:
        print(f"PHASE F AGENT JSON EXPORT: FAIL: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
