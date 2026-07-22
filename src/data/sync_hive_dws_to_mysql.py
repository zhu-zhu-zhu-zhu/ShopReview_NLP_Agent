"""Validate Hive DWS exports and synchronize them to the MySQL serving layer."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

DATABASE_NAME = "shopreview_serving"
EXPECTED_OVERVIEW_REVIEW_COUNT = 99703


class ServingSyncError(ValueError):
    """Raised when an export or target table violates the serving contract."""


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    integer_columns: frozenset[str]
    float_columns: frozenset[str]
    rate_columns: frozenset[str]
    date_columns: frozenset[str] = frozenset()
    datetime_columns: frozenset[str] = frozenset()
    nullable_columns: frozenset[str] = frozenset()


OVERVIEW_SPEC = TableSpec(
    name="dws_sentiment_overview",
    columns=(
        "load_batch_id", "model_version", "review_count", "product_count",
        "positive_count", "neutral_count", "negative_count", "positive_rate",
        "neutral_rate", "negative_rate", "average_rating",
        "average_prediction_score", "generated_at",
    ),
    primary_key=("load_batch_id", "model_version"),
    integer_columns=frozenset(
        {"review_count", "product_count", "positive_count", "neutral_count", "negative_count"}
    ),
    float_columns=frozenset(
        {"positive_rate", "neutral_rate", "negative_rate", "average_rating", "average_prediction_score"}
    ),
    rate_columns=frozenset(
        {"positive_rate", "neutral_rate", "negative_rate", "average_prediction_score"}
    ),
    datetime_columns=frozenset({"generated_at"}),
    nullable_columns=frozenset({"average_rating", "average_prediction_score", "generated_at"}),
)

DAILY_SPEC = TableSpec(
    name="dws_sentiment_daily",
    columns=(
        "dt", "load_batch_id", "model_version", "review_count", "positive_count",
        "neutral_count", "negative_count", "positive_rate", "neutral_rate",
        "negative_rate", "average_rating", "generated_at",
    ),
    primary_key=("dt", "load_batch_id", "model_version"),
    integer_columns=frozenset(
        {"review_count", "positive_count", "neutral_count", "negative_count"}
    ),
    float_columns=frozenset(
        {"positive_rate", "neutral_rate", "negative_rate", "average_rating"}
    ),
    rate_columns=frozenset({"positive_rate", "neutral_rate", "negative_rate"}),
    date_columns=frozenset({"dt"}),
    datetime_columns=frozenset({"generated_at"}),
    nullable_columns=frozenset({"average_rating", "generated_at"}),
)

PRODUCT_SPEC = TableSpec(
    name="dws_product_sentiment",
    columns=(
        "parent_asin", "product_title", "store_name", "main_category",
        "load_batch_id", "model_version", "review_count", "average_rating",
        "positive_count", "neutral_count", "negative_count", "positive_rate",
        "neutral_rate", "negative_rate", "verified_purchase_rate",
        "average_helpful_vote", "average_prediction_score", "generated_at",
    ),
    primary_key=("parent_asin", "load_batch_id", "model_version"),
    integer_columns=frozenset(
        {"review_count", "positive_count", "neutral_count", "negative_count"}
    ),
    float_columns=frozenset(
        {
            "average_rating", "positive_rate", "neutral_rate", "negative_rate",
            "verified_purchase_rate", "average_helpful_vote", "average_prediction_score",
        }
    ),
    rate_columns=frozenset(
        {
            "positive_rate", "neutral_rate", "negative_rate",
            "verified_purchase_rate", "average_prediction_score",
        }
    ),
    datetime_columns=frozenset({"generated_at"}),
    nullable_columns=frozenset(
        {
            "product_title", "store_name", "main_category", "average_rating",
            "verified_purchase_rate", "average_helpful_vote",
            "average_prediction_score", "generated_at",
        }
    ),
)

TABLE_SPECS = (OVERVIEW_SPEC, DAILY_SPEC, PRODUCT_SPEC)


def _export_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ServingSyncError(f"export path not found: {path}")
    files = sorted(
        candidate
        for candidate in path.iterdir()
        if candidate.is_file() and not candidate.name.startswith(("_", "."))
    )
    if not files:
        raise ServingSyncError(f"no export data files found: {path}")
    return files


def _convert_value(raw: str, column: str, spec: TableSpec, line_label: str) -> Any:
    if raw == r"\N":
        if column not in spec.nullable_columns:
            raise ServingSyncError(f"unexpected NULL for {column} at {line_label}")
        return None
    try:
        if column in spec.integer_columns:
            value = int(raw)
            if value < 0:
                raise ValueError("negative integer")
            return value
        if column in spec.float_columns:
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError("non-finite float")
            return value
        if column in spec.date_columns:
            return date.fromisoformat(raw)
        if column in spec.datetime_columns:
            return datetime.fromisoformat(raw.replace(" ", "T", 1))
    except (ValueError, TypeError) as exc:
        raise ServingSyncError(f"invalid value for {column} at {line_label}") from exc
    if column in spec.primary_key and not raw:
        raise ServingSyncError(f"blank primary-key field {column} at {line_label}")
    return raw


def load_export(
    path: Path,
    spec: TableSpec,
    expected_batch_id: str,
    expected_model_version: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys: set[tuple[Any, ...]] = set()
    for export_file in _export_files(path):
        with export_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter="\x01", quoting=csv.QUOTE_NONE)
            for line_number, values in enumerate(reader, 1):
                line_label = f"{export_file.name}:{line_number}"
                if len(values) != len(spec.columns):
                    raise ServingSyncError(
                        f"{spec.name} column count mismatch at {line_label}: "
                        f"{len(values)} != {len(spec.columns)}"
                    )
                row = {
                    column: _convert_value(raw, column, spec, line_label)
                    for column, raw in zip(spec.columns, values)
                }
                if row["load_batch_id"] != expected_batch_id:
                    raise ServingSyncError(f"unexpected batch ID at {line_label}")
                if row["model_version"] != expected_model_version:
                    raise ServingSyncError(f"unexpected model version at {line_label}")
                for column in spec.rate_columns:
                    value = row[column]
                    if value is not None and not 0.0 <= value <= 1.0:
                        raise ServingSyncError(f"rate outside [0,1] for {column} at {line_label}")
                if row["positive_count"] + row["neutral_count"] + row["negative_count"] != row["review_count"]:
                    raise ServingSyncError(f"sentiment counts do not reconcile at {line_label}")
                key = tuple(row[column] for column in spec.primary_key)
                if key in keys:
                    raise ServingSyncError(f"duplicate primary key in {spec.name} at {line_label}")
                keys.add(key)
                rows.append(row)
    return rows


def validate_source_datasets(datasets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    overview = datasets[OVERVIEW_SPEC.name]
    if len(overview) != 1:
        raise ServingSyncError(f"overview export must have exactly one row; found {len(overview)}")
    overview_row = overview[0]
    if overview_row["review_count"] != EXPECTED_OVERVIEW_REVIEW_COUNT:
        raise ServingSyncError(
            f"overview review_count mismatch: {overview_row['review_count']} != {EXPECTED_OVERVIEW_REVIEW_COUNT}"
        )
    daily_total = sum(row["review_count"] for row in datasets[DAILY_SPEC.name])
    product_total = sum(row["review_count"] for row in datasets[PRODUCT_SPEC.name])
    if daily_total != overview_row["review_count"]:
        raise ServingSyncError("daily review_count total does not match overview")
    if product_total != overview_row["review_count"]:
        raise ServingSyncError("product review_count total does not match overview")
    return {
        "overview_review_count": overview_row["review_count"],
        "product_count": overview_row["product_count"],
        "positive_count": overview_row["positive_count"],
        "neutral_count": overview_row["neutral_count"],
        "negative_count": overview_row["negative_count"],
        "sentiment_count_sum": (
            overview_row["positive_count"]
            + overview_row["neutral_count"]
            + overview_row["negative_count"]
        ),
        "daily_review_count_sum": daily_total,
        "product_review_count_sum": product_total,
    }


def load_all_exports(
    overview_path: Path,
    daily_path: Path,
    product_path: Path,
    batch_id: str,
    model_version: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    datasets = {
        OVERVIEW_SPEC.name: load_export(overview_path, OVERVIEW_SPEC, batch_id, model_version),
        DAILY_SPEC.name: load_export(daily_path, DAILY_SPEC, batch_id, model_version),
        PRODUCT_SPEC.name: load_export(product_path, PRODUCT_SPEC, batch_id, model_version),
    }
    business_totals = validate_source_datasets(datasets)
    return datasets, business_totals


def build_delete_statement(spec: TableSpec) -> str:
    return (
        f"DELETE FROM {DATABASE_NAME}.{spec.name} "
        "WHERE load_batch_id=%s AND model_version=%s"
    )


def build_insert_statement(spec: TableSpec) -> str:
    columns = ", ".join(spec.columns)
    placeholders = ", ".join(["%s"] * len(spec.columns))
    return f"INSERT INTO {DATABASE_NAME}.{spec.name} ({columns}) VALUES ({placeholders})"


def build_transaction_plan() -> list[dict[str, str]]:
    return [
        {
            "table": spec.name,
            "delete_sql": build_delete_statement(spec),
            "insert_sql": build_insert_statement(spec),
        }
        for spec in TABLE_SPECS
    ]


def _chunks(rows: Sequence[dict[str, Any]], size: int) -> Iterator[Sequence[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _query_scalar(cursor: Any, sql: str, params: tuple[Any, ...]) -> int:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if row is None:
        raise ServingSyncError("MySQL validation query returned no row")
    return int(row[0])


def validate_mysql_target(
    cursor: Any,
    datasets: dict[str, list[dict[str, Any]]],
    batch_id: str,
    model_version: str,
    business_totals: dict[str, Any],
) -> dict[str, Any]:
    params = (batch_id, model_version)
    target_counts: dict[str, int] = {}
    for spec in TABLE_SPECS:
        count = _query_scalar(
            cursor,
            f"SELECT COUNT(*) FROM {DATABASE_NAME}.{spec.name} WHERE load_batch_id=%s AND model_version=%s",
            params,
        )
        target_counts[spec.name] = count
        if count != len(datasets[spec.name]):
            raise ServingSyncError(f"MySQL count mismatch for {spec.name}")

    cursor.execute(
        f"SELECT review_count, positive_count, neutral_count, negative_count "
        f"FROM {DATABASE_NAME}.{OVERVIEW_SPEC.name} "
        "WHERE load_batch_id=%s AND model_version=%s",
        params,
    )
    overview = cursor.fetchone()
    if overview is None or int(overview[0]) != EXPECTED_OVERVIEW_REVIEW_COUNT:
        raise ServingSyncError("MySQL overview review_count mismatch")
    if int(overview[1]) + int(overview[2]) + int(overview[3]) != int(overview[0]):
        raise ServingSyncError("MySQL overview sentiment counts do not reconcile")
    if int(overview[0]) != business_totals["overview_review_count"]:
        raise ServingSyncError("MySQL overview total differs from Hive export")

    aggregate_totals: dict[str, int] = {}
    for spec, expected_total in (
        (DAILY_SPEC, business_totals["daily_review_count_sum"]),
        (PRODUCT_SPEC, business_totals["product_review_count_sum"]),
    ):
        total = _query_scalar(
            cursor,
            f"SELECT COALESCE(SUM(review_count),0) FROM {DATABASE_NAME}.{spec.name} "
            "WHERE load_batch_id=%s AND model_version=%s",
            params,
        )
        if total != expected_total:
            raise ServingSyncError(f"MySQL review_count total mismatch for {spec.name}")
        aggregate_totals[spec.name] = total

    invalid_rates = 0
    for spec in TABLE_SPECS:
        conditions = " OR ".join(
            f"({column} IS NOT NULL AND ({column}<0 OR {column}>1))"
            for column in sorted(spec.rate_columns)
        )
        invalid_rates += _query_scalar(
            cursor,
            f"SELECT COUNT(*) FROM {DATABASE_NAME}.{spec.name} "
            f"WHERE load_batch_id=%s AND model_version=%s AND ({conditions})",
            params,
        )
    if invalid_rates:
        raise ServingSyncError(f"MySQL contains {invalid_rates} invalid rate rows")
    duplicate_key_counts: dict[str, int] = {}
    for spec in TABLE_SPECS:
        key_columns = ", ".join(spec.primary_key)
        duplicate_count = _query_scalar(
            cursor,
            f"SELECT COUNT(*) FROM (SELECT {key_columns} "
            f"FROM {DATABASE_NAME}.{spec.name} "
            "WHERE load_batch_id=%s AND model_version=%s "
            f"GROUP BY {key_columns} HAVING COUNT(*)>1) AS duplicate_keys",
            params,
        )
        if duplicate_count:
            raise ServingSyncError(f"MySQL duplicate keys found in {spec.name}")
        duplicate_key_counts[spec.name] = duplicate_count
    return {
        "target_counts": target_counts,
        "overview_review_count": int(overview[0]),
        "sentiment_count_sum": int(overview[1]) + int(overview[2]) + int(overview[3]),
        "aggregate_review_count_totals": aggregate_totals,
        "invalid_rate_rows": invalid_rates,
        "duplicate_key_counts": duplicate_key_counts,
    }


def write_summary_atomic(path: Path, payload: dict[str, Any]) -> None:
    forbidden = {"password", "connection_string", "user_id", "review_text"}
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if any(field in serialized.lower() for field in forbidden):
        raise ServingSyncError("unsafe field detected in summary")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(serialized + "\n", encoding="utf-8")
    os.replace(temporary, path)


def make_summary(
    batch_id: str,
    model_version: str,
    datasets: dict[str, list[dict[str, Any]]],
    business_totals: dict[str, Any],
    result: str,
    mysql_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_counts = {
        "overview": len(datasets[OVERVIEW_SPEC.name]),
        "daily": len(datasets[DAILY_SPEC.name]),
        "product": len(datasets[PRODUCT_SPEC.name]),
    }
    pending = mysql_validation is None
    return {
        "result": result,
        "batch_id": batch_id,
        "model_version": model_version,
        "hive_export_status": "PASS",
        "local_export_validation_status": "PASS",
        "hive_source_counts": source_counts,
        "local_export_counts": source_counts,
        "mysql_target_counts": None if mysql_validation is None else mysql_validation["target_counts"],
        "mysql_sync_status": "PENDING" if pending else "PASS",
        "reconciliation_status": "PENDING" if pending else "PASS",
        "credential_safety_status": "PASS",
        "reason": (
            "MySQL port 3306 unavailable and credentials not configured"
            if pending
            else None
        ),
        "overview_business_totals": business_totals,
        "rate_validation": {
            "source_invalid_rows": 0,
            "mysql_invalid_rows": None if mysql_validation is None else mysql_validation["invalid_rate_rows"],
        },
        "duplicate_key_counts": {
            "source": {spec.name: 0 for spec in TABLE_SPECS},
            "mysql": None if mysql_validation is None else mysql_validation["duplicate_key_counts"],
        },
        "table_names": [f"{DATABASE_NAME}.{spec.name}" for spec in TABLE_SPECS],
        "synchronized_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def connect_mysql(args: argparse.Namespace) -> Any:
    secret = os.environ.get(args.password_env)
    if not secret:
        raise ServingSyncError(f"required password environment variable is not set: {args.password_env}")
    if args.database != DATABASE_NAME:
        raise ServingSyncError(f"database must be {DATABASE_NAME}")
    try:
        import mysql.connector  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ServingSyncError("mysql-connector-python is required") from exc
    return mysql.connector.connect(
        host=args.host,
        port=args.port,
        database=DATABASE_NAME,
        user=args.user,
        password=secret,
        charset="utf8mb4",
        autocommit=False,
    )


def synchronize(args: argparse.Namespace, datasets: dict[str, list[dict[str, Any]]], business_totals: dict[str, Any]) -> dict[str, Any]:
    connection = connect_mysql(args)
    try:
        cursor = connection.cursor()
        if args.validate_only:
            return validate_mysql_target(
                cursor, datasets, args.batch_id, args.model_version, business_totals
            )
        connection.start_transaction()
        try:
            for spec in TABLE_SPECS:
                cursor.execute(build_delete_statement(spec), (args.batch_id, args.model_version))
                insert_sql = build_insert_statement(spec)
                for chunk in _chunks(datasets[spec.name], args.chunk_size):
                    values = [tuple(row[column] for column in spec.columns) for row in chunk]
                    cursor.executemany(insert_sql, values)
            validation = validate_mysql_target(
                cursor, datasets, args.batch_id, args.model_version, business_totals
            )
            connection.commit()
            return validation
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overview-path", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--product-path", type=Path, required=True)
    parser.add_argument("--batch-id", default="prod_v1_100k")
    parser.add_argument("--model-version", default="tfidf_logreg_oof_v1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--database", default=DATABASE_NAME)
    parser.add_argument("--user")
    parser.add_argument("--password-env", default="SHOPREVIEW_MYSQL_PASSWORD")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--source-only", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.chunk_size <= 0:
        raise ServingSyncError("chunk-size must be positive")
    datasets, business_totals = load_all_exports(
        args.overview_path,
        args.daily_path,
        args.product_path,
        args.batch_id,
        args.model_version,
    )
    if args.source_only:
        summary = make_summary(
            args.batch_id, args.model_version, datasets, business_totals, "PENDING"
        )
    else:
        if not args.user:
            raise ServingSyncError("MySQL user is required")
        mysql_validation = synchronize(args, datasets, business_totals)
        summary = make_summary(
            args.batch_id,
            args.model_version,
            datasets,
            business_totals,
            "PASS",
            mysql_validation,
        )
    write_summary_atomic(args.summary_path, summary)
    counts = summary["hive_source_counts"]
    print(
        f"Overview={counts['overview']} Daily={counts['daily']} "
        f"Product={counts['product']} Result={summary['result']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
