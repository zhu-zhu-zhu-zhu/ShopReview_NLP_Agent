#!/usr/bin/env python3
"""Validate the synthetic Phase F aspect fixture and create Hive-safe text."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DELIMITER = "\x01"
NULL_VALUE = r"\N"
ALLOWED_ASPECTS = {
    "size", "color", "material", "comfort", "workmanship",
    "description_mismatch", "packaging", "delivery", "price", "other",
}
VALID_SENTIMENTS = {"negative", "neutral", "positive"}
REQUIRED_FIELDS = (
    "review_key", "aspect", "reason_code", "reason_name", "aspect_sentiment",
    "confidence", "extractor_version", "extracted_at",
)
CONTRACT_KEY = ("review_key", "aspect", "reason_code", "extractor_version")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _required_text(record: dict[str, Any], field: str, index: int) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"record {index}: {field} must be a non-empty string")
    return value


def _validate_utc_timestamp(value: str, index: int) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"record {index}: extracted_at is not an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"record {index}: extracted_at must be a UTC timestamp")


def validate_records(records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list) or not records:
        raise ValueError("fixture must be a non-empty JSON array")
    validated: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"record {index}: expected an object")
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            raise ValueError(f"record {index}: missing required field(s): {', '.join(missing)}")
        unknown = sorted(set(record).difference(REQUIRED_FIELDS))
        if unknown:
            raise ValueError(f"record {index}: unknown field(s): {', '.join(unknown)}")
        for field in REQUIRED_FIELDS:
            if field != "confidence":
                _required_text(record, field, index)
        if record["aspect"] not in ALLOWED_ASPECTS:
            raise ValueError(f"record {index}: invalid aspect {record['aspect']!r}")
        if record["aspect_sentiment"] not in VALID_SENTIMENTS:
            raise ValueError(f"record {index}: invalid aspect_sentiment {record['aspect_sentiment']!r}")
        confidence = record["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError(f"record {index}: confidence must be between 0 and 1")
        _validate_utc_timestamp(record["extracted_at"], index)
        key = tuple(record[field] for field in CONTRACT_KEY)
        if key in seen:
            raise ValueError(f"record {index}: duplicate aspect contract key")
        seen.add(key)
        validated.append({field: record[field] for field in REQUIRED_FIELDS})
    return validated


def load_fixture(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return validate_records(json.load(handle))


def hive_safe(value: Any) -> str:
    if value is None:
        return NULL_VALUE
    text = str(value)
    return text.replace(DELIMITER, " ").replace("\r", " ").replace("\n", " ").replace("\t", " ")


def to_control_a(records: list[dict[str, Any]]) -> str:
    return "".join(DELIMITER.join(hive_safe(record[field]) for field in REQUIRED_FIELDS) + "\n" for record in records)


def prepare(fixture_path: Path, output_path: Path) -> int:
    records = load_fixture(fixture_path)
    atomic_write(output_path, to_control_a(records))
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        count = prepare(args.fixture, args.output)
    except Exception as exc:
        print(f"PHASE F ASPECT PREPARATION: FAIL: {type(exc).__name__}: {exc}")
        return 1
    print(f"PHASE F ASPECT PREPARATION: PASS: rows={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
