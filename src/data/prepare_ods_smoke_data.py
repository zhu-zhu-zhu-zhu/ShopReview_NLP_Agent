#!/usr/bin/env python3
"""Convert only the 100-row Amazon Fashion samples into Hive-safe text."""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DELIMITER = "\x01"
NULL = r"\N"
EXPECTED_ROWS = 100
REVIEW_COLUMNS = [
    "rating", "title", "review_text", "images_json", "asin", "parent_asin",
    "user_id", "review_timestamp", "helpful_vote", "verified_purchase",
]
META_COLUMNS = [
    "main_category", "product_title", "average_rating", "rating_number",
    "features_json", "description_json", "price_raw", "images_json",
    "videos_json", "store_name", "categories_json", "details_json",
    "parent_asin", "bought_together_json",
]


def sanitize_string(value: str) -> str:
    return value.replace(DELIMITER, " ").replace("\r", " ").replace("\n", " ").replace("\t", " ")


def sanitize_nested(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, list):
        return [sanitize_nested(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_nested(item) for key, item in value.items()}
    return value


def string_value(value: Any) -> str:
    if value is None:
        return NULL
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, (list, dict)):
        return nested_json(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return sanitize_string(str(value))


def nested_json(value: Any) -> str:
    if value is None:
        return NULL
    return json.dumps(sanitize_nested(value), ensure_ascii=False, separators=(",", ":"))


def number_value(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return NULL
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return NULL
        return str(value)
    if isinstance(value, str):
        cleaned = value.strip()
        try:
            number = float(cleaned)
        except ValueError:
            return NULL
        return cleaned if math.isfinite(number) else NULL
    return NULL


def integer_value(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return NULL
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return str(int(value))
    if isinstance(value, str):
        cleaned = value.strip()
        try:
            return str(int(cleaned))
        except ValueError:
            return NULL
    return NULL


def boolean_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return NULL


def raw_price_value(value: Any) -> str:
    if value is None:
        return NULL
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, (list, dict)):
        return nested_json(value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def convert_review(obj: dict[str, Any]) -> list[str]:
    return [
        number_value(obj.get("rating")),
        string_value(obj.get("title")),
        string_value(obj.get("text")),
        nested_json(obj.get("images")),
        string_value(obj.get("asin")),
        string_value(obj.get("parent_asin")),
        string_value(obj.get("user_id")),
        integer_value(obj.get("timestamp")),
        integer_value(obj.get("helpful_vote")),
        boolean_value(obj.get("verified_purchase")),
    ]


def convert_metadata(obj: dict[str, Any]) -> list[str]:
    return [
        string_value(obj.get("main_category")),
        string_value(obj.get("title")),
        number_value(obj.get("average_rating")),
        integer_value(obj.get("rating_number")),
        nested_json(obj.get("features")),
        nested_json(obj.get("description")),
        raw_price_value(obj.get("price")),
        nested_json(obj.get("images")),
        nested_json(obj.get("videos")),
        string_value(obj.get("store")),
        nested_json(obj.get("categories")),
        nested_json(obj.get("details")),
        string_value(obj.get("parent_asin")),
        nested_json(obj.get("bought_together")),
    ]


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def convert_file(source: Path, destination: Path, converter: Callable[[dict[str, Any]], list[str]],
                 expected_columns: int) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(f"Sample file not found: {source}")
    rows: list[str] = []
    physical = valid = 0
    with source.open("r", encoding="utf-8") as handle:
        for physical, line in enumerate(handle, 1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Malformed JSON at {source.name}:{physical}: {exc.msg}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"Non-object JSON at {source.name}:{physical}")
            fields = converter(obj)
            if len(fields) != expected_columns:
                raise ValueError(f"Unexpected converted column count at {source.name}:{physical}")
            if any(DELIMITER in field or "\r" in field or "\n" in field or "\t" in field for field in fields):
                raise ValueError(f"Unsafe control character remained at {source.name}:{physical}")
            rows.append(DELIMITER.join(fields))
            valid += 1
    if physical != EXPECTED_ROWS or valid != EXPECTED_ROWS:
        raise ValueError(f"Expected exactly {EXPECTED_ROWS} objects in {source.name}; got physical={physical}, valid={valid}")
    atomic_text(destination, "\n".join(rows) + "\n")
    return {"source_filename": source.name, "physical_rows": physical, "valid_rows": valid,
            "converted_rows": len(rows), "output_filename": destination.name,
            "column_count": expected_columns}


def run(review_sample: Path, meta_sample: Path, output_dir: Path) -> dict[str, Any]:
    review_output = output_dir / "ods_review_smoke.txt"
    meta_output = output_dir / "ods_meta_smoke.txt"
    review_summary = convert_file(review_sample, review_output, convert_review, len(REVIEW_COLUMNS))
    meta_summary = convert_file(meta_sample, meta_output, convert_metadata, len(META_COLUMNS))
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "delimiter": "ASCII control-A (0x01)", "null_representation": NULL,
        "review_columns": REVIEW_COLUMNS, "metadata_columns": META_COLUMNS,
        "review": review_summary, "metadata": meta_summary,
        "completion_status": "successful",
    }
    atomic_text(output_dir / "conversion_summary.json",
                json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-sample", required=True, type=Path)
    parser.add_argument("--meta-sample", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        summary = run(args.review_sample, args.meta_sample, args.output_dir)
    except Exception as exc:
        print(f"ODS SMOKE CONVERSION: FAIL: {type(exc).__name__}: {exc}")
        return 1
    print(f"ODS SMOKE CONVERSION: PASS: review={summary['review']['converted_rows']} metadata={summary['metadata']['converted_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
