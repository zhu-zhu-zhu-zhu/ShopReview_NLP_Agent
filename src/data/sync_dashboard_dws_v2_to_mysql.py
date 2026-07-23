"""Validate bounded DWS v2 exports and transactionally synchronize MySQL."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

DATABASE_NAME = "shopreview_serving"
EXPECTED_REVIEWS = 99_703
EXPECTED_NEGATIVE = 15_899
EXPECTED_V1_COUNTS = {
    "dws_sentiment_overview": 1,
    "dws_sentiment_daily": 4_137,
    "dws_product_sentiment": 76_784,
}
TABLE_METADATA = {
    "dws_sentiment_overview": ("batch + model", "KPI overview", "/api/overview"),
    "dws_sentiment_daily": ("day + batch + model", "daily trend", "/api/trends/daily"),
    "dws_product_sentiment": ("product + batch + model", "product ranking", "/api/products"),
    "dws_category_sentiment": ("category + batch + model", "category comparison", "/api/categories"),
    "dws_store_sentiment": ("store + batch + model", "store ranking", "/api/stores"),
    "dws_verified_purchase_sentiment": ("purchase status + batch + model", "purchase comparison", "/api/verified-purchase"),
    "dws_rating_prediction_matrix": ("rating + prediction + batch + model", "rating heatmap", "/api/rating-matrix"),
    "dws_prediction_confidence": ("confidence bucket + batch + model", "confidence distribution", "/api/confidence"),
    "dws_monthly_sentiment": ("month + batch + model", "monthly trend", "/api/trends/monthly"),
    "dws_sentiment_alerts": ("alert", "risk alerts", "/api/alerts"),
    "dws_review_samples": ("safe sample + batch + model", "representative cards", "/api/samples"),
    "dws_aspect_summary": ("aspect + batch + model", "keyword-rule aspects", "/api/aspects"),
    "dws_negative_reasons": ("reason + batch + model", "keyword-rule negative reasons", "/api/negative-reasons"),
}


class DashboardSyncError(ValueError):
    pass


@dataclass(frozen=True)
class TableSpec:
    name: str
    export_name: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    integers: frozenset[str] = frozenset()
    floats: frozenset[str] = frozenset()
    dates: frozenset[str] = frozenset()
    datetimes: frozenset[str] = frozenset()
    nullable: frozenset[str] = frozenset()
    rates: frozenset[str] = frozenset()
    sentiment_reconcile: bool = False


def _spec(name: str, export_name: str, columns: str, key: str, **kwargs: Any) -> TableSpec:
    converted = {k: frozenset(v.split()) if isinstance(v, str) else v for k, v in kwargs.items()}
    return TableSpec(name, export_name, tuple(columns.split()), tuple(key.split()), **converted)


TABLE_SPECS = (
    _spec("dws_category_sentiment", "category", "category_key main_category review_count product_count average_rating positive_count neutral_count negative_count positive_rate neutral_rate negative_rate average_prediction_score generated_at load_batch_id model_version", "category_key load_batch_id model_version", integers="review_count product_count positive_count neutral_count negative_count", floats="average_rating positive_rate neutral_rate negative_rate average_prediction_score", datetimes="generated_at", nullable="average_rating average_prediction_score generated_at", rates="positive_rate neutral_rate negative_rate average_prediction_score", sentiment_reconcile=True),
    _spec("dws_store_sentiment", "store", "store_key store_name review_count product_count average_rating positive_count neutral_count negative_count positive_rate neutral_rate negative_rate average_prediction_score generated_at load_batch_id model_version", "store_key load_batch_id model_version", integers="review_count product_count positive_count neutral_count negative_count", floats="average_rating positive_rate neutral_rate negative_rate average_prediction_score", datetimes="generated_at", nullable="average_rating average_prediction_score generated_at", rates="positive_rate neutral_rate negative_rate average_prediction_score", sentiment_reconcile=True),
    _spec("dws_verified_purchase_sentiment", "verified_purchase", "purchase_status review_count positive_count neutral_count negative_count positive_rate neutral_rate negative_rate average_rating average_helpful_vote average_prediction_score generated_at load_batch_id model_version", "purchase_status load_batch_id model_version", integers="review_count positive_count neutral_count negative_count", floats="positive_rate neutral_rate negative_rate average_rating average_helpful_vote average_prediction_score", datetimes="generated_at", nullable="average_rating average_helpful_vote average_prediction_score generated_at", rates="positive_rate neutral_rate negative_rate average_prediction_score", sentiment_reconcile=True),
    _spec("dws_rating_prediction_matrix", "rating_matrix", "rating_value pred_label review_count rate_within_rating generated_at load_batch_id model_version", "rating_value pred_label load_batch_id model_version", integers="rating_value review_count", floats="rate_within_rating", datetimes="generated_at", nullable="generated_at", rates="rate_within_rating"),
    _spec("dws_prediction_confidence", "confidence", "bucket_code bucket_order minimum_score maximum_score review_count positive_count neutral_count negative_count average_prediction_score generated_at load_batch_id model_version", "bucket_code load_batch_id model_version", integers="bucket_order review_count positive_count neutral_count negative_count", floats="minimum_score maximum_score average_prediction_score", datetimes="generated_at", nullable="average_prediction_score generated_at", rates="minimum_score maximum_score average_prediction_score", sentiment_reconcile=True),
    _spec("dws_monthly_sentiment", "monthly", "month_id review_count product_count positive_count neutral_count negative_count positive_rate neutral_rate negative_rate average_rating average_prediction_score generated_at load_batch_id model_version", "month_id load_batch_id model_version", integers="review_count product_count positive_count neutral_count negative_count", floats="positive_rate neutral_rate negative_rate average_rating average_prediction_score", datetimes="generated_at", nullable="average_rating average_prediction_score generated_at", rates="positive_rate neutral_rate negative_rate average_prediction_score", sentiment_reconcile=True),
    _spec("dws_sentiment_alerts", "alerts", "alert_id alert_type alert_level entity_type entity_id entity_name metric_name metric_value threshold_value review_count alert_message generated_at load_batch_id model_version", "alert_id", integers="review_count", floats="metric_value threshold_value", datetimes="generated_at", nullable="entity_name generated_at"),
    _spec("dws_review_samples", "samples", "sample_id parent_asin product_title main_category rating pred_label pred_score review_text_preview text_length review_time sample_rank generated_at load_batch_id model_version", "sample_id load_batch_id model_version", integers="text_length sample_rank", floats="rating pred_score", datetimes="review_time generated_at", nullable="parent_asin product_title main_category review_text_preview review_time generated_at", rates="pred_score"),
    _spec("dws_aspect_summary", "aspects", "aspect_code aspect_name mention_count product_count positive_count neutral_count negative_count positive_rate neutral_rate negative_rate average_prediction_score extraction_method rule_version generated_at load_batch_id model_version", "aspect_code load_batch_id model_version", integers="mention_count product_count positive_count neutral_count negative_count", floats="positive_rate neutral_rate negative_rate average_prediction_score", datetimes="generated_at", nullable="average_prediction_score generated_at", rates="positive_rate neutral_rate negative_rate average_prediction_score"),
    _spec("dws_negative_reasons", "reasons", "reason_code reason_name mention_count product_count share_of_negative_reviews average_prediction_score extraction_method rule_version generated_at load_batch_id model_version", "reason_code load_batch_id model_version", integers="mention_count product_count", floats="share_of_negative_reviews average_prediction_score", datetimes="generated_at", nullable="average_prediction_score generated_at", rates="share_of_negative_reviews average_prediction_score"),
)
SPEC_BY_NAME = {spec.name: spec for spec in TABLE_SPECS}

ASPECT_RULES = {
    "quality": r"quality|well made|poorly made|cheaply made|craftsmanship|defect|defective|flimsy",
    "size_fit": r"size|sizing|fit|fits|fitting|too small|too big|too large|tight|loose",
    "material": r"material|fabric|cotton|polyester|leather|wool|texture",
    "comfort": r"comfort|comfortable|uncomfortable|soft|itchy|scratchy|hurts",
    "appearance": r"color|colour|style|design|look|appearance|cute|beautiful|ugly",
    "price_value": r"price|value|worth|expensive|cheap|overpriced|cost",
    "shipping_packaging": r"shipping|delivery|arrived|package|packaging|late delivery|damaged box",
    "durability": r"durable|durability|lasted|lasting|broke|broken|tear|torn|wear out",
}
NEGATIVE_REASON_RULES = {
    "poor_quality": r"poor quality|bad quality|cheaply made|poorly made|defective|flimsy",
    "wrong_size": r"too small|too large|too big|wrong size|doesn.t fit|did not fit|tight|loose",
    "color_mismatch": r"wrong color|different color|color mismatch|faded|not the color",
    "damaged_item": r"damaged|broken|torn|stained|cracked|defective",
    "not_as_described": r"not as described|different from picture|not like picture|misleading description",
    "uncomfortable": r"uncomfortable|itchy|scratchy|hurts|painful",
    "overpriced": r"overpriced|not worth|too expensive|waste of money",
    "delivery_issue": r"late delivery|arrived late|shipping issue|damaged package|missing package",
    "return_issue": r"return|refund|replacement|exchange",
}


def normalize_entity(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return text or "Unknown"


def verified_purchase_group(value: Any) -> str:
    if value is True or str(value).strip().lower() == "true":
        return "verified"
    if value is False or str(value).strip().lower() == "false":
        return "unverified"
    return "unknown"


def confidence_bucket(score: float) -> str:
    if not 0 <= score <= 1:
        raise DashboardSyncError("confidence score outside [0,1]")
    return "low" if score < .5 else "medium" if score < .75 else "high" if score < .9 else "very_high"


def validate_month_id(value: str) -> bool:
    return re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value) is not None


def sanitize_preview(value: str | None, limit: int = 180) -> str:
    return re.sub(r"[\x00-\x1f\x7f]+", " ", value or "")[:limit]


def match_rules(text: str | None, rules: dict[str, str]) -> set[str]:
    lowered = (text or "").lower()
    return {code for code, pattern in rules.items() if re.search(pattern, lowered)}


def match_aspects(text: str | None) -> set[str]:
    return match_rules(text, ASPECT_RULES)


def match_negative_reasons(text: str | None) -> set[str]:
    return match_rules(text, NEGATIVE_REASON_RULES)


def assert_no_forbidden_fields(columns: Iterable[str]) -> None:
    forbidden = {"user_id", "review_key", "review_text"}
    found = forbidden.intersection(columns)
    if found:
        raise DashboardSyncError(f"forbidden fields: {sorted(found)}")


def _files(path: Path) -> list[Path]:
    files = [path] if path.is_file() else sorted(p for p in path.glob("*") if p.is_file() and not p.name.startswith(("_", ".")))
    if not files:
        raise DashboardSyncError(f"no export files found: {path}")
    return files


def _convert(raw: str, column: str, spec: TableSpec, label: str) -> Any:
    if raw == r"\N":
        if column not in spec.nullable:
            raise DashboardSyncError(f"unexpected NULL for {column} at {label}")
        return None
    try:
        if column in spec.integers:
            value = int(raw)
            if value < 0:
                raise ValueError
            return value
        if column in spec.floats:
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError
            return value
        if column in spec.dates:
            return date.fromisoformat(raw)
        if column in spec.datetimes:
            return datetime.fromisoformat(raw.replace(" ", "T", 1))
    except (TypeError, ValueError) as exc:
        raise DashboardSyncError(f"invalid {column} at {label}") from exc
    return raw


def load_export(path: Path, spec: TableSpec, batch_id: str, model_version: str) -> list[dict[str, Any]]:
    assert_no_forbidden_fields(spec.columns)
    rows: list[dict[str, Any]] = []
    keys: set[tuple[Any, ...]] = set()
    for file in _files(path):
        with file.open(encoding="utf-8", newline="") as handle:
            for number, values in enumerate(csv.reader(handle, delimiter="\x01", quoting=csv.QUOTE_NONE), 1):
                label = f"{file.name}:{number}"
                if len(values) != len(spec.columns):
                    raise DashboardSyncError(f"column count mismatch at {label}")
                row = {column: _convert(raw, column, spec, label) for column, raw in zip(spec.columns, values)}
                if row["load_batch_id"] != batch_id:
                    raise DashboardSyncError(f"unexpected batch at {label}")
                if row["model_version"] != model_version:
                    raise DashboardSyncError(f"unexpected model at {label}")
                for column in spec.rates:
                    if row[column] is not None and not 0 <= row[column] <= 1:
                        raise DashboardSyncError(f"rate outside [0,1] at {label}")
                if spec.sentiment_reconcile and row["review_count"] != row["positive_count"] + row["neutral_count"] + row["negative_count"]:
                    raise DashboardSyncError(f"sentiment count mismatch at {label}")
                key = tuple(row[column] for column in spec.primary_key)
                if key in keys:
                    raise DashboardSyncError(f"duplicate primary key at {label}")
                keys.add(key)
                rows.append(row)
    _validate_special(spec, rows)
    return rows


def _validate_special(spec: TableSpec, rows: list[dict[str, Any]]) -> None:
    if spec.name == "dws_rating_prediction_matrix":
        sums: dict[int, float] = {}
        for row in rows:
            if row["rating_value"] not in range(1, 6) or row["pred_label"] not in {"negative", "neutral", "positive"}:
                raise DashboardSyncError("invalid rating matrix value")
            sums[row["rating_value"]] = sums.get(row["rating_value"], 0) + row["rate_within_rating"]
        if any(abs(value - 1) > 1e-6 for value in sums.values()):
            raise DashboardSyncError("rating matrix rates do not reconcile")
    elif spec.name == "dws_monthly_sentiment" and any(not validate_month_id(row["month_id"]) for row in rows):
        raise DashboardSyncError("invalid month_id")
    elif spec.name == "dws_review_samples":
        counts = {label: 0 for label in ("negative", "neutral", "positive")}
        for row in rows:
            if row["pred_label"] not in counts or len(row["review_text_preview"] or "") > 180 or sanitize_preview(row["review_text_preview"]) != (row["review_text_preview"] or ""):
                raise DashboardSyncError("unsafe review sample")
            counts[row["pred_label"]] += 1
        if len(rows) > 150 or any(count > 50 for count in counts.values()):
            raise DashboardSyncError("sample limit exceeded")
    elif spec.name == "dws_aspect_summary":
        for row in rows:
            if row["extraction_method"] != "keyword_rules_v1" or row["rule_version"] != "fashion_aspects_v1" or row["mention_count"] != row["positive_count"] + row["neutral_count"] + row["negative_count"]:
                raise DashboardSyncError("invalid aspect contract")
    elif spec.name == "dws_negative_reasons":
        if any(row["extraction_method"] != "keyword_rules_v1" or row["rule_version"] != "negative_reasons_v1" or row["mention_count"] > EXPECTED_NEGATIVE for row in rows):
            raise DashboardSyncError("invalid negative-reason contract")


def validate_business_totals(datasets: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    names = ("dws_category_sentiment", "dws_store_sentiment", "dws_verified_purchase_sentiment", "dws_rating_prediction_matrix", "dws_prediction_confidence", "dws_monthly_sentiment")
    totals = {name: sum(row["review_count"] for row in datasets[name]) for name in names}
    if any(total != EXPECTED_REVIEWS for total in totals.values()):
        raise DashboardSyncError(f"source reconciliation failed: {totals}")
    return totals


def build_delete_statement(spec: TableSpec) -> str:
    return f"DELETE FROM {DATABASE_NAME}.{spec.name} WHERE load_batch_id=%s AND model_version=%s"


def build_insert_statement(spec: TableSpec) -> str:
    return f"INSERT INTO {DATABASE_NAME}.{spec.name} ({', '.join(spec.columns)}) VALUES ({', '.join(['%s'] * len(spec.columns))})"


def _chunks(rows: Sequence[dict[str, Any]], size: int) -> Iterator[Sequence[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def _scalar(cursor: Any, sql: str, params: tuple[Any, ...] = ()) -> int:
    cursor.execute(sql, params)
    result = cursor.fetchone()
    if result is None:
        raise DashboardSyncError("validation query returned no row")
    return int(result[0])


def validate_mysql(cursor: Any, datasets: dict[str, list[dict[str, Any]]], batch_id: str, model_version: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table, expected in EXPECTED_V1_COUNTS.items():
        count = _scalar(cursor, f"SELECT COUNT(*) FROM {DATABASE_NAME}.{table} WHERE load_batch_id=%s AND model_version=%s", (batch_id, model_version))
        if count != expected:
            raise DashboardSyncError(f"existing table changed: {table}={count}")
        counts[table] = count
    overview_total = _scalar(cursor, f"SELECT review_count FROM {DATABASE_NAME}.dws_sentiment_overview WHERE load_batch_id=%s AND model_version=%s", (batch_id, model_version))
    if overview_total != EXPECTED_REVIEWS:
        raise DashboardSyncError("overview review_count changed")
    for spec in TABLE_SPECS:
        count = _scalar(cursor, f"SELECT COUNT(*) FROM {DATABASE_NAME}.{spec.name} WHERE load_batch_id=%s AND model_version=%s", (batch_id, model_version))
        if count != len(datasets[spec.name]):
            raise DashboardSyncError(f"MySQL reconciliation failed: {spec.name}")
        counts[spec.name] = count
    return counts


def connect(args: argparse.Namespace) -> Any:
    password = os.environ.get(args.password_env)
    if not password:
        raise DashboardSyncError("required password environment variable is not set")
    try:
        import mysql.connector  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DashboardSyncError("mysql-connector-python is required") from exc
    return mysql.connector.connect(host=args.host, port=args.port, database=DATABASE_NAME, user=args.user, password=password, charset="utf8mb4", autocommit=False)


def synchronize(args: argparse.Namespace, datasets: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    connection = connect(args)
    try:
        cursor = connection.cursor()
        if args.validate_only:
            return validate_mysql(cursor, datasets, args.batch_id, args.model_version)
        connection.start_transaction()
        try:
            for spec in TABLE_SPECS:
                cursor.execute(build_delete_statement(spec), (args.batch_id, args.model_version))
                for chunk in _chunks(datasets[spec.name], args.chunk_size):
                    cursor.executemany(build_insert_statement(spec), [tuple(row[column] for column in spec.columns) for row in chunk])
            counts = validate_mysql(cursor, datasets, args.batch_id, args.model_version)
            connection.commit()
            return counts
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()


def make_summary(batch_id: str, model_version: str, datasets: dict[str, list[dict[str, Any]]], totals: dict[str, int], mysql_counts: dict[str, int]) -> dict[str, Any]:
    return {
        "result": "PASS", "batch_id": batch_id, "model_version": model_version,
        "hive_export_counts": {name: len(rows) for name, rows in datasets.items()},
        "source_review_totals": totals, "mysql_counts": mysql_counts,
        "existing_v1_counts_preserved": EXPECTED_V1_COUNTS,
        "aspect_extraction_method": "keyword_rules_v1", "negative_reason_extraction_method": "keyword_rules_v1",
        "synchronized_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def write_safe_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if re.search(r"password|credential|user_id", text, re.I):
        raise DashboardSyncError("unsafe summary content")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def write_manifest(path: Path, batch_id: str, model_version: str, hive_counts: dict[str, int], mysql_counts: dict[str, int]) -> None:
    if set(hive_counts) != set(TABLE_METADATA) or set(mysql_counts) != set(TABLE_METADATA):
        raise DashboardSyncError("manifest requires exactly 13 serving tables")
    primary_keys = {
        "dws_sentiment_overview": "load_batch_id + model_version",
        "dws_sentiment_daily": "dt + load_batch_id + model_version",
        "dws_product_sentiment": "parent_asin + load_batch_id + model_version",
        **{spec.name: " + ".join(spec.primary_key) for spec in TABLE_SPECS},
    }
    important_fields = {
        "dws_sentiment_overview": "review_count, positive/neutral/negative_count",
        "dws_sentiment_daily": "dt, review_count, sentiment rates",
        "dws_product_sentiment": "parent_asin, product_title, review_count, negative_rate",
        "dws_category_sentiment": "main_category, review_count, sentiment rates",
        "dws_store_sentiment": "store_name, review_count, negative_rate",
        "dws_verified_purchase_sentiment": "purchase_status, review_count, sentiment rates",
        "dws_rating_prediction_matrix": "rating_value, pred_label, rate_within_rating",
        "dws_prediction_confidence": "bucket_code, review_count, average_prediction_score",
        "dws_monthly_sentiment": "month_id, review_count, sentiment rates",
        "dws_sentiment_alerts": "alert_type, alert_level, metric_value, threshold_value",
        "dws_review_samples": "pred_label, pred_score, review_text_preview",
        "dws_aspect_summary": "aspect_code, mention_count, sentiment rates, rule_version",
        "dws_negative_reasons": "reason_code, mention_count, share_of_negative_reviews, rule_version",
    }
    source_types = {
        **{name: "production Hive DWS v1" for name in EXPECTED_V1_COUNTS},
        **{spec.name: "production Hive DWS v2 aggregate" for spec in TABLE_SPECS},
        "dws_review_samples": "bounded sanitized real-data preview",
        "dws_aspect_summary": "deterministic keyword_rules_v1",
        "dws_negative_reasons": "deterministic keyword_rules_v1",
    }
    lines = [
        "# MySQL Serving v2 Table Manifest", "",
        f"- Batch: `{batch_id}`", f"- Model version: `{model_version}`",
        "- Reconciliation: `PASS`", "",
        "| Table | Primary key | Grain | Important fields | Hive rows | MySQL rows | Source type | Dashboard/API use |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for table, (grain, purpose, route) in TABLE_METADATA.items():
        if hive_counts[table] != mysql_counts[table]:
            raise DashboardSyncError(f"manifest reconciliation failed: {table}")
        lines.append(
            f"| `{table}` | {primary_keys[table]} | {grain} | {important_fields[table]} | "
            f"{hive_counts[table]} | {mysql_counts[table]} | {source_types[table]} | {purpose}; `{route}` |"
        )
    lines += [
        "", "## Rule-based tables", "",
        "`dws_aspect_summary` uses `extraction_method=keyword_rules_v1` and `rule_version=fashion_aspects_v1`.",
        "`dws_negative_reasons` uses `extraction_method=keyword_rules_v1` and `rule_version=negative_reasons_v1`.",
        "These are deterministic keyword-rule results, not LLM, BERT, or learned aspect-model outputs.", "",
    ]
    text = "\n".join(lines)
    if re.search(r"password|credential|user_id", text, re.I):
        raise DashboardSyncError("unsafe manifest content")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--batch-id", default="prod_v1_100k")
    parser.add_argument("--model-version", default="tfidf_logreg_oof_v1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password-env", default="SHOPREVIEW_MYSQL_PASSWORD")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--hive-counts-path", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    datasets = {spec.name: load_export(args.export_root / spec.export_name, spec, args.batch_id, args.model_version) for spec in TABLE_SPECS}
    totals = validate_business_totals(datasets)
    mysql_counts = synchronize(args, datasets)
    hive_counts = json.loads(args.hive_counts_path.read_text(encoding="utf-8"))
    write_manifest(args.manifest_path, args.batch_id, args.model_version, hive_counts, mysql_counts)
    write_safe_json(args.summary_path, make_summary(args.batch_id, args.model_version, datasets, totals, mysql_counts))
    print("DWSv2Tables=10 MySQLTables=13 Reconciliation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
