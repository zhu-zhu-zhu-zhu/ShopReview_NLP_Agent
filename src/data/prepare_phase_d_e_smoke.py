#!/usr/bin/env python3
"""Prepare a bounded, coordinated Amazon Fashion Phase D/E smoke dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.data.prepare_ods_smoke_data import DELIMITER, convert_metadata, convert_review


META_VALID_LIMIT = 50_000
REVIEW_VALID_LIMIT = 100_000
TARGET_PAIRS = 50
MINIMUM_PAIRS = 20
VALID_LABELS = {"negative", "neutral", "positive"}


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


def key_part(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def review_key(review: dict[str, Any]) -> str:
    payload = "|#|".join(key_part(review.get(field)) for field in (
        "user_id", "asin", "parent_asin", "timestamp", "title", "text"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_review_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ").replace("\t", " ")).strip()


def weak_label(value: Any) -> str:
    if isinstance(value, bool):
        return "unknown"
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if rating <= 2:
        return "negative"
    if rating == 3:
        return "neutral"
    if rating >= 4:
        return "positive"
    return "unknown"


def iter_valid_objects(path: Path, valid_limit: int):
    valid = 0
    physical = 0
    malformed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            physical += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(obj, dict):
                malformed += 1
                continue
            valid += 1
            yield obj, physical, valid, malformed
            if valid >= valid_limit:
                break


def collect_pairs(meta_path: Path, review_path: Path, target_pairs: int = TARGET_PAIRS,
                  meta_limit: int = META_VALID_LIMIT,
                  review_limit: int = REVIEW_VALID_LIMIT):
    metadata: dict[str, dict[str, Any]] = {}
    meta_physical = meta_valid = meta_malformed = 0
    for obj, meta_physical, meta_valid, meta_malformed in iter_valid_objects(meta_path, meta_limit):
        parent = obj.get("parent_asin")
        if isinstance(parent, str) and parent.strip() and parent not in metadata:
            metadata[parent] = obj

    reviews: list[dict[str, Any]] = []
    matched_meta: list[dict[str, Any]] = []
    selected: set[str] = set()
    review_physical = review_valid = review_malformed = 0
    for obj, review_physical, review_valid, review_malformed in iter_valid_objects(review_path, review_limit):
        parent = obj.get("parent_asin")
        if isinstance(parent, str) and parent in metadata and parent not in selected:
            selected.add(parent)
            reviews.append(obj)
            matched_meta.append(metadata[parent])
            if len(reviews) >= target_pairs:
                break
    stats = {
        "metadata_physical_lines_read": meta_physical,
        "metadata_valid_objects_read": meta_valid,
        "metadata_malformed_or_non_object": meta_malformed,
        "metadata_unique_parent_asin_in_map": len(metadata),
        "review_physical_lines_read": review_physical,
        "review_valid_objects_read": review_valid,
        "review_malformed_or_non_object": review_malformed,
        "matched_pair_count": len(reviews),
    }
    return reviews, matched_meta, stats


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    atomic_text(path, "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records))


def write_delimited(path: Path, records: list[dict[str, Any]], converter) -> None:
    rows = [DELIMITER.join(converter(record)) for record in records]
    atomic_text(path, "\n".join(rows) + "\n")


def build_nlp_records(reviews: list[dict[str, Any]], metadata: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for review, meta in zip(reviews, metadata):
        cleaned = clean_review_text(review.get("text"))
        label = weak_label(review.get("rating"))
        if not cleaned or label not in VALID_LABELS:
            continue
        output.append({
            "review_key": review_key(review), "review_text_clean": cleaned,
            "rating_label": label, "rating": review.get("rating"),
            "parent_asin": review.get("parent_asin"),
            "main_category": meta.get("main_category"),
        })
    return output


def run(review_path: Path, meta_path: Path, output_dir: Path,
        target_pairs: int = TARGET_PAIRS, minimum_pairs: int = MINIMUM_PAIRS) -> dict[str, Any]:
    if not review_path.is_file() or not meta_path.is_file():
        raise FileNotFoundError("Both raw source files are required")
    reviews, metadata, stats = collect_pairs(meta_path, review_path, target_pairs)
    if len(reviews) < minimum_pairs:
        raise ValueError(f"Only {len(reviews)} matched pairs found; at least {minimum_pairs} required")
    if len(reviews) != len(metadata):
        raise ValueError("Matched review and metadata counts differ")
    nlp_records = build_nlp_records(reviews, metadata)
    review_keys = [record["review_key"] for record in nlp_records]
    if len(review_keys) != len(set(review_keys)):
        raise ValueError("NLP input review_key values are not unique")
    write_jsonl(output_dir / "matched_reviews.jsonl", reviews)
    write_jsonl(output_dir / "matched_metadata.jsonl", metadata)
    write_delimited(output_dir / "ods_review_matched.txt", reviews, convert_review)
    write_delimited(output_dir / "ods_meta_matched.txt", metadata, convert_metadata)
    write_jsonl(output_dir / "nlp_input_smoke.jsonl", nlp_records)
    label_counts: dict[str, int] = {label: 0 for label in sorted(VALID_LABELS)}
    for record in nlp_records:
        label_counts[record["rating_label"]] += 1
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "bounded coordinated smoke sample; not full-dataset statistics",
        "metadata_valid_limit": META_VALID_LIMIT, "review_valid_limit": REVIEW_VALID_LIMIT,
        "target_pair_count": target_pairs, **stats,
        "converted_review_rows": len(reviews), "converted_metadata_rows": len(metadata),
        "dwd_eligible_nlp_rows": len(nlp_records), "filtered_ineligible_rows": len(reviews) - len(nlp_records),
        "weak_label_distribution": label_counts,
        "review_key_algorithm": "sha256(user_id + '|#|' + asin + '|#|' + parent_asin + '|#|' + timestamp + '|#|' + title + '|#|' + text), UTF-8, missing values empty, lowercase hex",
        "completion_status": "successful",
    }
    atomic_text(output_dir / "preparation_summary.json", json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-path", required=True, type=Path)
    parser.add_argument("--meta-path", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--target-pairs", type=int, default=TARGET_PAIRS)
    parser.add_argument("--minimum-pairs", type=int, default=MINIMUM_PAIRS)
    args = parser.parse_args()
    try:
        summary = run(args.review_path, args.meta_path, args.output_dir, args.target_pairs, args.minimum_pairs)
    except Exception as exc:
        print(f"PHASE D/E PREPARATION: FAIL: {type(exc).__name__}: {exc}")
        return 1
    print(f"PHASE D/E PREPARATION: PASS: pairs={summary['matched_pair_count']} nlp_rows={summary['dwd_eligible_nlp_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
