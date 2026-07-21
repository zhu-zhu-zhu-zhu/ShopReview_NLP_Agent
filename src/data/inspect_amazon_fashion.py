#!/usr/bin/env python3
"""Bounded, streaming inspection for Amazon Reviews 2023 Amazon_Fashion JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCOPE_LABEL = "Sample inspection only — not a complete dataset statistic."
VERSION = "2.0.0-bounded"
REVIEW_LIMIT = 100_000
META_LIMIT = 50_000
REVIEW_EXPECTED = [
    "rating", "title", "text", "images", "asin", "parent_asin",
    "user_id", "timestamp", "helpful_vote", "verified_purchase",
]
META_EXPECTED = [
    "main_category", "title", "average_rating", "rating_number", "features",
    "description", "price", "images", "videos", "store", "categories",
    "details", "parent_asin", "bought_together",
]
MEANINGS = {
    "rating": "Review star rating", "title": "Review or product title",
    "text": "Review body text", "images": "Image information",
    "asin": "Amazon item identifier", "parent_asin": "Parent product identifier and join key",
    "user_id": "Reviewer identifier", "timestamp": "Review event timestamp",
    "helpful_vote": "Helpful-vote count", "verified_purchase": "Verified-purchase indicator",
    "main_category": "Primary product category", "average_rating": "Product average rating",
    "rating_number": "Product rating count", "features": "Product feature list",
    "description": "Product description", "price": "Product price",
    "videos": "Video information", "store": "Store or brand name",
    "categories": "Product category hierarchy", "details": "Product detail attributes",
    "bought_together": "Frequently bought-together information",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def parse_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
        return result if math.isfinite(result) else None
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        if not cleaned:
            return None
        try:
            result = float(cleaned)
            return result if math.isfinite(result) else None
        except ValueError:
            return None
    return None


def parse_timestamp(value: Any) -> tuple[float, datetime] | None:
    number = parse_number(value)
    if number is not None:
        seconds = number / 1000.0 if abs(number) >= 100_000_000_000 else number
        try:
            return number, datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp(), parsed.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def canonical_number(number: float) -> str:
    return str(int(number)) if number.is_integer() else format(number, ".12g")


def missing_or_blank(obj: dict[str, Any], field: str) -> bool:
    value = obj.get(field)
    return field not in obj or value is None or (isinstance(value, str) and not value.strip())


def new_common() -> dict[str, Any]:
    return {
        "physical_lines_inspected": 0, "blank_lines": 0, "valid_object_count": 0,
        "malformed_json_count": 0, "non_object_json_count": 0,
        "malformed_examples": [], "field_occurrence": Counter(),
        "field_null": Counter(), "field_blank_string": Counter(), "field_types": {},
    }


def observe_fields(common: dict[str, Any], obj: dict[str, Any]) -> None:
    for field, value in obj.items():
        common["field_occurrence"][field] += 1
        if value is None:
            common["field_null"][field] += 1
        if isinstance(value, str) and not value.strip():
            common["field_blank_string"][field] += 1
        common["field_types"].setdefault(field, Counter())[value_type(value)] += 1


def finalize_common(common: dict[str, Any]) -> dict[str, Any]:
    result = dict(common)
    fields = sorted(common["field_occurrence"])
    result["observed_fields"] = fields
    result["field_occurrence"] = {field: common["field_occurrence"][field] for field in fields}
    result["field_null"] = {field: common["field_null"].get(field, 0) for field in fields}
    result["field_blank_string"] = {
        field: common["field_blank_string"].get(field, 0) for field in fields
    }
    result["field_types"] = {
        field: dict(sorted(common["field_types"][field].items())) for field in fields
    }
    return result


def update_reservoir(sample: list[dict[str, Any]], obj: dict[str, Any], count: int,
                     size: int, rng: random.Random) -> None:
    if len(sample) < size:
        sample.append(obj)
        return
    position = rng.randint(1, count)
    if position <= size:
        sample[position - 1] = obj


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


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def atomic_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    atomic_text(path, "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    ))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parsed_objects(path: Path, limit: int, label: str, common: dict[str, Any],
                   progress_every: int):
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line_number > limit:
                break
            common["physical_lines_inspected"] += 1
            if progress_every and line_number % progress_every == 0:
                print(f"[{label}] inspected {line_number:,} physical lines", flush=True)
            if not line.strip():
                common["blank_lines"] += 1
                continue
            try:
                value = json.loads(line)
            except (json.JSONDecodeError, UnicodeError) as exc:
                common["malformed_json_count"] += 1
                if len(common["malformed_examples"]) < 5:
                    common["malformed_examples"].append({
                        "line": line_number, "error": type(exc).__name__,
                        "message": str(exc).splitlines()[0][:160],
                    })
                continue
            if not isinstance(value, dict):
                common["non_object_json_count"] += 1
                continue
            common["valid_object_count"] += 1
            observe_fields(common, value)
            yield value


def scan_metadata(path: Path, limit: int, sample_size: int, seed: int,
                  progress_every: int) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    common = new_common()
    sample: list[dict[str, Any]] = []
    rng = random.Random(seed)
    parent_asins: set[str] = set()
    for obj in parsed_objects(path, limit, "metadata", common, progress_every):
        update_reservoir(sample, obj, common["valid_object_count"], sample_size, rng)
        parent = obj.get("parent_asin")
        if isinstance(parent, str) and parent.strip():
            parent_asins.add(parent.strip())
    result = finalize_common(common)
    result["distinct_parent_asin_within_sample"] = len(parent_asins)
    result["scope_label"] = SCOPE_LABEL
    return result, sample, parent_asins


def scan_reviews(path: Path, metadata_parents: set[str], limit: int, sample_size: int,
                 seed: int, progress_every: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    common = new_common()
    sample: list[dict[str, Any]] = []
    rng = random.Random(seed)
    rating_distribution: Counter[str] = Counter()
    weak_distribution: Counter[str] = Counter()
    verified_distribution: Counter[str] = Counter()
    stats: dict[str, Any] = {
        "missing_review_text_count": 0, "null_review_text_count": 0,
        "blank_review_text_count": 0, "invalid_rating_count": 0,
        "rating_outside_1_to_5_count": 0, "timestamp_valid_count": 0,
        "timestamp_invalid_or_missing_count": 0, "timestamp_minimum_raw": None,
        "timestamp_maximum_raw": None, "timestamp_minimum_utc": None,
        "timestamp_maximum_utc": None, "helpful_vote_valid_count": 0,
        "helpful_vote_invalid_or_missing_count": 0, "helpful_vote_minimum": None,
        "helpful_vote_maximum": None, "helpful_vote_sum": 0.0,
        "helpful_vote_zero_count": 0, "reviews_with_parent_asin": 0,
        "matched_parent_asin_rows": 0, "unmatched_parent_asin_rows": 0,
        "missing_or_blank_parent_asin_rows": 0,
    }
    for obj in parsed_objects(path, limit, "reviews", common, progress_every):
        update_reservoir(sample, obj, common["valid_object_count"], sample_size, rng)
        if "text" not in obj:
            stats["missing_review_text_count"] += 1
        elif obj["text"] is None:
            stats["null_review_text_count"] += 1
        elif isinstance(obj["text"], str) and not obj["text"].strip():
            stats["blank_review_text_count"] += 1
        rating = parse_number(obj.get("rating"))
        if rating is None:
            stats["invalid_rating_count"] += 1
        else:
            rating_distribution[canonical_number(rating)] += 1
            if rating < 1 or rating > 5:
                stats["rating_outside_1_to_5_count"] += 1
            elif rating <= 2:
                weak_distribution["negative"] += 1
            elif rating == 3:
                weak_distribution["neutral"] += 1
            elif rating >= 4:
                weak_distribution["positive"] += 1
        verified = obj.get("verified_purchase")
        verified_distribution[f"{value_type(verified)}:{str(verified).lower()}"] += 1
        parsed_time = parse_timestamp(obj.get("timestamp"))
        if parsed_time is None:
            stats["timestamp_invalid_or_missing_count"] += 1
        else:
            raw, dt = parsed_time
            stats["timestamp_valid_count"] += 1
            stats["timestamp_minimum_raw"] = raw if stats["timestamp_minimum_raw"] is None else min(stats["timestamp_minimum_raw"], raw)
            stats["timestamp_maximum_raw"] = raw if stats["timestamp_maximum_raw"] is None else max(stats["timestamp_maximum_raw"], raw)
            iso = dt.isoformat()
            stats["timestamp_minimum_utc"] = iso if stats["timestamp_minimum_utc"] is None else min(stats["timestamp_minimum_utc"], iso)
            stats["timestamp_maximum_utc"] = iso if stats["timestamp_maximum_utc"] is None else max(stats["timestamp_maximum_utc"], iso)
        helpful = parse_number(obj.get("helpful_vote"))
        if helpful is None or helpful < 0:
            stats["helpful_vote_invalid_or_missing_count"] += 1
        else:
            stats["helpful_vote_valid_count"] += 1
            stats["helpful_vote_sum"] += helpful
            stats["helpful_vote_minimum"] = helpful if stats["helpful_vote_minimum"] is None else min(stats["helpful_vote_minimum"], helpful)
            stats["helpful_vote_maximum"] = helpful if stats["helpful_vote_maximum"] is None else max(stats["helpful_vote_maximum"], helpful)
            if helpful == 0:
                stats["helpful_vote_zero_count"] += 1
        parent = obj.get("parent_asin")
        if isinstance(parent, str) and parent.strip():
            stats["reviews_with_parent_asin"] += 1
            if parent.strip() in metadata_parents:
                stats["matched_parent_asin_rows"] += 1
            else:
                stats["unmatched_parent_asin_rows"] += 1
        else:
            stats["missing_or_blank_parent_asin_rows"] += 1
    result = finalize_common(common)
    result.update(stats)
    result["helpful_vote_mean"] = (
        result.pop("helpful_vote_sum") / result["helpful_vote_valid_count"]
        if result["helpful_vote_valid_count"] else None
    )
    result["rating_distribution"] = dict(sorted(rating_distribution.items()))
    result["weak_sentiment_distribution"] = dict(sorted(weak_distribution.items()))
    result["verified_purchase_distribution"] = dict(sorted(verified_distribution.items()))
    denominator = result["reviews_with_parent_asin"]
    result["sample_parent_asin_join_rate"] = (
        result["matched_parent_asin_rows"] / denominator if denominator else 0.0
    )
    result["scope_label"] = SCOPE_LABEL
    return result, sample


def proposed_hive_type(types: dict[str, int]) -> str:
    observed = set(types) - {"null"}
    if observed <= {"integer"} and observed:
        return "BIGINT"
    if observed <= {"integer", "number"} and observed:
        return "DOUBLE"
    if observed <= {"boolean"} and observed:
        return "BOOLEAN"
    if observed <= {"array"} and observed:
        return "ARRAY<STRING>"
    return "STRING"


def dictionary_rows(dataset: str, profile: dict[str, Any], expected: list[str]) -> list[dict[str, Any]]:
    rows = []
    observed = set(profile["observed_fields"])
    valid = profile["valid_object_count"]
    for field in sorted(observed | set(expected)):
        presence = profile["field_occurrence"].get(field, 0)
        types = profile["field_types"].get(field, {})
        if field not in observed:
            status = "Missing in bounded sample"
        elif field not in expected:
            status = "Unexpected in bounded sample"
        elif presence < valid:
            status = "Optional in bounded sample"
        else:
            status = "Observed in bounded sample"
        rows.append({
            "dataset": dataset, "field": field, "presence": presence, "types": types,
            "nullable": presence < valid or types.get("null", 0) > 0,
            "meaning": MEANINGS.get(field, "Meaning requires team confirmation"),
            "target": field, "hive_type": proposed_hive_type(types), "status": status,
        })
    return rows


def render_dictionary(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Amazon Fashion Data Dictionary", "", f"> {SCOPE_LABEL}",
        "> Proposed warehouse names and Hive types are Draft.", "",
        "| Dataset | Field | Presence | Observed types | Nullable | Meaning | Target | Draft Hive type | Status |",
        "|---|---|---:|---|---|---|---|---|---|",
    ]
    for row in rows:
        types = ", ".join(f"{key}:{value}" for key, value in row["types"].items()) or "—"
        cells = [row["dataset"], f"`{row['field']}`", f"{row['presence']:,}", types,
                 "Yes" if row["nullable"] else "No", row["meaning"], f"`{row['target']}`",
                 f"`{row['hive_type']}`", row["status"]]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in cells) + " |")
    lines.extend(["", f"> {SCOPE_LABEL}", ""])
    return "\n".join(lines)


def render_report(profile: dict[str, Any]) -> str:
    review = profile["review_profile"]
    meta = profile["metadata_profile"]
    ratings = ", ".join(f"{key}: {value:,}" for key, value in review["rating_distribution"].items())
    weak = ", ".join(f"{key}: {value:,}" for key, value in review["weak_sentiment_distribution"].items())
    verified = ", ".join(f"{key}: {value:,}" for key, value in review["verified_purchase_distribution"].items())
    empty_text = review["missing_review_text_count"] + review["null_review_text_count"] + review["blank_review_text_count"]
    lines = [
        "# Amazon Fashion Dataset Inspection Report", "", f"> **{SCOPE_LABEL}**", "",
        "## 1. Inspection Scope", "",
        f"The first **{profile['limits']['review_physical_lines']:,}** review physical lines and first **{profile['limits']['metadata_physical_lines']:,}** metadata physical lines were inspected. Results describe only these bounded leading subsets.", "",
        "## 2. Source Files", "",
        f"- `{profile['sources']['review']['filename']}` ({profile['sources']['review']['byte_size']:,} bytes)",
        f"- `{profile['sources']['metadata']['filename']}` ({profile['sources']['metadata']['byte_size']:,} bytes)", "",
        "## 3. Inspection Method", "",
        "Python standard-library JSON parsing processed one UTF-8 line at a time. No pandas load, SQLite, HDFS, Hive or NLP model was used. Deterministic reservoir samples use seed 42. Raw files remained read-only.", "",
        "## 4. Review Subset Summary", "",
        f"- Physical lines inspected: {review['physical_lines_inspected']:,}",
        f"- Valid JSON objects: {review['valid_object_count']:,}",
        f"- Malformed JSON: {review['malformed_json_count']:,}",
        f"- Blank lines: {review['blank_lines']:,}",
        f"- Missing/null/blank review text: {empty_text:,}",
        f"- Timestamp range (UTC): {review['timestamp_minimum_utc']} to {review['timestamp_maximum_utc']}",
        f"- Helpful votes: valid={review['helpful_vote_valid_count']:,}, invalid/missing={review['helpful_vote_invalid_or_missing_count']:,}, min={review['helpful_vote_minimum']}, max={review['helpful_vote_maximum']}, mean={review['helpful_vote_mean']}",
        f"- Verified purchase distribution: {verified}", "",
        "## 5. Metadata Subset Summary", "",
        f"- Physical lines inspected: {meta['physical_lines_inspected']:,}",
        f"- Valid JSON objects: {meta['valid_object_count']:,}",
        f"- Malformed JSON: {meta['malformed_json_count']:,}",
        f"- Blank lines: {meta['blank_lines']:,}", "",
        "## 6. Observed Fields", "",
        "Review: " + ", ".join(f"`{field}`" for field in review["observed_fields"]), "",
        "Metadata: " + ", ".join(f"`{field}`" for field in meta["observed_fields"]), "",
        f"> {SCOPE_LABEL}", "",
        "## 7. Rating and Weak Sentiment Distribution", "",
        f"Ratings: {ratings}", "",
        f"Rating-based weak labels: {weak}", "",
        "Weak labels are derived from ratings (1–2 negative, 3 neutral, 4–5 positive); they are not NLP predictions.", "",
        "## 8. Parent ASIN Join Check", "",
        f"Within the two inspected leading subsets, {review['matched_parent_asin_rows']:,} of {review['reviews_with_parent_asin']:,} review rows with non-empty `parent_asin` matched an inspected metadata `parent_asin`.",
        f"Sample join rate: **{review['sample_parent_asin_join_rate']:.6%}**.",
        "This is not a full-dataset join rate because metadata outside the first bounded subset was not considered.", "",
        "## 9. Local Sampling", "",
        "Reservoir sampling generated 100 review objects and 100 metadata objects with seed 42. These real-record JSONL samples are ignored and remain local.", "",
        "## 10. Warehouse Implications", "",
        "The observed two-source schema supports separate review and metadata ODS tables, timestamp conversion in DWD, explicit empty-text rules, a `parent_asin` join, nullable metadata handling and rating-based weak-label generation. All Hive types remain Draft pending broader validation.", "",
        "## 11. Limitations", "",
        "- Only a bounded leading subset was inspected; every result in this report is a sample statistic.",
        "- Exact full-dataset counts, distinct counts, duplicate counts and join quality will be calculated later with Hive.",
        "- No NLP model was executed.",
        "- No HDFS or Hive work was executed.", "",
        "## 12. Recommended Next Step", "",
        "Review this checkpoint with the team, then prepare Draft HDFS landing and ODS schemas without claiming full-dataset statistics.", "",
        f"> **{SCOPE_LABEL}**", "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-path", required=True, type=Path)
    parser.add_argument("--meta-path", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--sample-dir", required=True, type=Path)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-review-lines", type=int, default=REVIEW_LIMIT)
    parser.add_argument("--max-meta-lines", type=int, default=META_LIMIT)
    parser.add_argument("--progress-every", type=int, default=10_000)
    parser.add_argument("--mode", choices=("smoke", "bounded"), required=True)
    return parser


def run_inspection(args: argparse.Namespace) -> dict[str, Any]:
    for source in (args.review_path, args.meta_path):
        if not source.is_file():
            raise FileNotFoundError(f"Required source not found: {source}")
    if args.max_review_lines < 1 or args.max_review_lines > REVIEW_LIMIT:
        raise ValueError(f"max-review-lines must be between 1 and {REVIEW_LIMIT}")
    if args.max_meta_lines < 1 or args.max_meta_lines > META_LIMIT:
        raise ValueError(f"max-meta-lines must be between 1 and {META_LIMIT}")
    if args.sample_size < 1:
        raise ValueError("sample-size must be positive")
    sources = {
        "review": {"filename": args.review_path.name, "byte_size": args.review_path.stat().st_size},
        "metadata": {"filename": args.meta_path.name, "byte_size": args.meta_path.stat().st_size},
    }
    meta_profile, meta_sample, metadata_parents = scan_metadata(
        args.meta_path, args.max_meta_lines, args.sample_size, args.seed, args.progress_every)
    review_profile, review_sample = scan_reviews(
        args.review_path, metadata_parents, args.max_review_lines,
        args.sample_size, args.seed, args.progress_every)
    review_sample_path = args.sample_dir / f"reviews_sample_{args.sample_size}.jsonl"
    meta_sample_path = args.sample_dir / f"meta_sample_{args.sample_size}.jsonl"
    atomic_jsonl(review_sample_path, review_sample)
    atomic_jsonl(meta_sample_path, meta_sample)
    schema = dictionary_rows("review", review_profile, REVIEW_EXPECTED) + dictionary_rows(
        "metadata", meta_profile, META_EXPECTED)
    profile = {
        "inspection_version": VERSION, "generated_at_utc": utc_now(), "mode": args.mode,
        "scope_label": SCOPE_LABEL, "completion_status": "successful",
        "limits": {"review_physical_lines": args.max_review_lines,
                   "metadata_physical_lines": args.max_meta_lines},
        "sources": sources, "review_profile": review_profile, "metadata_profile": meta_profile,
        "schema_profile": schema,
        "sampling": {
            "algorithm": "reservoir sampling", "seed": args.seed,
            "review_sample_size": len(review_sample), "metadata_sample_size": len(meta_sample),
            "review_sample_filename": review_sample_path.name,
            "metadata_sample_filename": meta_sample_path.name,
            "review_sample_sha256": sha256_file(review_sample_path),
            "metadata_sample_sha256": sha256_file(meta_sample_path),
        },
        "limitations": [
            "Only bounded leading subsets were inspected.",
            "Exact full counts will be calculated later with Hive.",
            "No NLP model was executed.", "No HDFS or Hive work was executed.",
        ],
    }
    atomic_json(args.output_json, profile)
    atomic_text(args.output_report, render_report(profile))
    atomic_text(Path("docs/DATA_DICTIONARY.md"), render_dictionary(schema))
    return profile


def main() -> int:
    args = build_parser().parse_args()
    try:
        profile = run_inspection(args)
    except Exception as exc:
        print(f"BOUNDED DATA INSPECTION FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(
        f"BOUNDED DATA INSPECTION COMPLETE: reviews={profile['review_profile']['physical_lines_inspected']:,} "
        f"metadata={profile['metadata_profile']['physical_lines_inspected']:,}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
