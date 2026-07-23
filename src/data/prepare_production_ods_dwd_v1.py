#!/usr/bin/env python3
"""Prepare the bounded Amazon Fashion production-v1 ODS source files."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, TextIO

from src.data.hive_text import DELIMITER, convert_metadata, convert_review


DEFAULT_REVIEW_LIMIT = 100_000
DEFAULT_BATCH_ID = "prod_v1_100k"
DEFAULT_PROGRESS_EVERY = 100_000
REVIEW_OUTPUT = "ods_amazon_fashion_review_prod_v1.txt"
META_OUTPUT = "ods_amazon_fashion_meta_prod_v1.txt"
SUMMARY_OUTPUT = "production_v1_summary.json"
MISSING_OUTPUT = "missing_metadata_parent_asin.txt"


@contextmanager
def atomic_writer(path: Path) -> Iterator[TextIO]:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            yield handle
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    with atomic_writer(path) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def converted_line(obj: dict[str, Any], converter, expected_columns: int) -> str:
    fields = converter(obj)
    if len(fields) != expected_columns:
        raise ValueError(f"converter returned {len(fields)} columns; expected {expected_columns}")
    if any(DELIMITER in field or "\r" in field or "\n" in field or "\t" in field for field in fields):
        raise ValueError("unsafe control character remained after conversion")
    return DELIMITER.join(fields)


def _progress(kind: str, physical: int, valid: int, progress_every: int) -> None:
    if progress_every > 0 and physical % progress_every == 0:
        print(f"{kind} progress: physical_lines={physical:,} valid_objects={valid:,}", flush=True)


def prepare(
    review_path: Path,
    meta_path: Path,
    output_dir: Path,
    review_limit: int = DEFAULT_REVIEW_LIMIT,
    batch_id: str = DEFAULT_BATCH_ID,
    progress_every: int = DEFAULT_PROGRESS_EVERY,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    if review_limit <= 0:
        raise ValueError("review_limit must be positive")
    if progress_every < 0:
        raise ValueError("progress_every cannot be negative")
    if not batch_id.strip():
        raise ValueError("batch_id cannot be blank")
    if not review_path.is_file() or not meta_path.is_file():
        raise FileNotFoundError("both raw source files are required")

    output_dir.mkdir(parents=True, exist_ok=True)
    review_output = output_dir / REVIEW_OUTPUT
    meta_output = output_dir / META_OUTPUT
    summary_output = output_dir / SUMMARY_OUTPUT
    missing_output = output_dir / MISSING_OUTPUT

    review_physical = review_valid = review_malformed = review_blank = 0
    review_rows = 0
    requested_parents: set[str] = set()
    with atomic_writer(review_output) as destination, review_path.open("r", encoding="utf-8") as source:
        for line in source:
            review_physical += 1
            if not line.strip():
                review_blank += 1
                _progress("review", review_physical, review_valid, progress_every)
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                review_malformed += 1
                _progress("review", review_physical, review_valid, progress_every)
                continue
            if not isinstance(obj, dict):
                review_malformed += 1
                _progress("review", review_physical, review_valid, progress_every)
                continue
            review_valid += 1
            destination.write(converted_line(obj, convert_review, 10) + "\n")
            review_rows += 1
            parent = obj.get("parent_asin")
            if isinstance(parent, str) and parent.strip():
                requested_parents.add(parent)
            _progress("review", review_physical, review_valid, progress_every)
            if review_valid >= review_limit:
                break

    if review_valid != review_limit:
        raise ValueError(f"source ended after {review_valid} valid reviews; required {review_limit}")

    metadata_physical = metadata_valid = metadata_malformed = metadata_blank = 0
    metadata_rows = 0
    matched_parents: set[str] = set()
    with atomic_writer(meta_output) as destination, meta_path.open("r", encoding="utf-8") as source:
        if requested_parents:
            for line in source:
                metadata_physical += 1
                if not line.strip():
                    metadata_blank += 1
                    _progress("metadata", metadata_physical, metadata_valid, progress_every)
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    metadata_malformed += 1
                    _progress("metadata", metadata_physical, metadata_valid, progress_every)
                    continue
                if not isinstance(obj, dict):
                    metadata_malformed += 1
                    _progress("metadata", metadata_physical, metadata_valid, progress_every)
                    continue
                metadata_valid += 1
                parent = obj.get("parent_asin")
                if isinstance(parent, str) and parent in requested_parents and parent not in matched_parents:
                    destination.write(converted_line(obj, convert_metadata, 14) + "\n")
                    metadata_rows += 1
                    matched_parents.add(parent)
                    if len(matched_parents) == len(requested_parents):
                        _progress("metadata", metadata_physical, metadata_valid, progress_every)
                        break
                _progress("metadata", metadata_physical, metadata_valid, progress_every)

    missing_parents = sorted(requested_parents.difference(matched_parents))
    with atomic_writer(missing_output) as handle:
        for parent in missing_parents:
            handle.write(parent + "\n")

    generated_at = generated_at_utc or datetime.now(timezone.utc).isoformat()
    summary = {
        "batch_id": batch_id,
        "review_limit": review_limit,
        "physical_review_lines_scanned": review_physical,
        "valid_reviews_selected": review_valid,
        "malformed_review_lines": review_malformed,
        "blank_review_lines": review_blank,
        "unique_review_parent_asin_count": len(requested_parents),
        "physical_metadata_lines_scanned": metadata_physical,
        "valid_metadata_objects_scanned": metadata_valid,
        "malformed_metadata_lines": metadata_malformed,
        "blank_metadata_lines": metadata_blank,
        "matched_metadata_count": len(matched_parents),
        "missing_metadata_parent_asin_count": len(missing_parents),
        "generated_review_file_rows": review_rows,
        "generated_metadata_file_rows": metadata_rows,
        "generated_at_utc": generated_at,
        "review_source_filename": review_path.name,
        "metadata_source_filename": meta_path.name,
        "review_source_bytes": review_path.stat().st_size,
        "metadata_source_bytes": meta_path.stat().st_size,
        "scope": "production-v1 experiment subset; not complete Amazon Fashion dataset statistics",
    }
    atomic_json(summary_output, summary)
    print(
        "PRODUCTION V1 PREPARATION: PASS: "
        f"reviews={review_rows:,} metadata={metadata_rows:,} missing_parent_asin={len(missing_parents):,}",
        flush=True,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-path", required=True, type=Path)
    parser.add_argument("--meta-path", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--review-limit", type=int, default=DEFAULT_REVIEW_LIMIT)
    parser.add_argument("--batch-id", default=DEFAULT_BATCH_ID)
    parser.add_argument("--progress-every", type=int, default=DEFAULT_PROGRESS_EVERY)
    args = parser.parse_args()
    try:
        prepare(
            args.review_path, args.meta_path, args.output_dir,
            review_limit=args.review_limit, batch_id=args.batch_id,
            progress_every=args.progress_every,
        )
    except Exception as exc:
        print(f"PRODUCTION V1 PREPARATION: FAIL: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
