from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.data.sync_hive_dws_to_mysql import (
    DAILY_SPEC,
    OVERVIEW_SPEC,
    PRODUCT_SPEC,
    ServingSyncError,
    build_delete_statement,
    build_insert_statement,
    build_transaction_plan,
    load_export,
    make_summary,
    write_summary_atomic,
)

BATCH = "prod_v1_100k"
MODEL = "tfidf_logreg_oof_v1"


def overview_values() -> list[str]:
    return [
        BATCH, MODEL, "99703", "76784", "64861", "18943", "15899",
        "0.6505", "0.1900", "0.1595", "4.1", "0.81", "2026-07-22 18:00:00",
    ]


def daily_values() -> list[str]:
    return [
        "2020-01-01", BATCH, MODEL, "99703", "64861", "18943", "15899",
        "0.6505", "0.1900", "0.1595", "4.1", "2026-07-22 18:00:00",
    ]


def product_values() -> list[str]:
    return [
        "PARENT001", "时尚连衣裙", "示例店铺", "AMAZON FASHION", BATCH, MODEL,
        "99703", "4.1", "64861", "18943", "15899", "0.6505", "0.1900",
        "0.1595", "0.91", "2.5", "0.81", "2026-07-22 18:00:00",
    ]


class HiveExportParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write(self, rows: list[list[str]]) -> Path:
        path = self.root / "part-00000"
        path.write_text(
            "".join("\x01".join(row) + "\n" for row in rows), encoding="utf-8"
        )
        return path

    def test_valid_overview_parsing(self) -> None:
        rows = load_export(self._write([overview_values()]), OVERVIEW_SPEC, BATCH, MODEL)
        self.assertEqual(rows[0]["review_count"], 99703)

    def test_valid_daily_parsing(self) -> None:
        rows = load_export(self._write([daily_values()]), DAILY_SPEC, BATCH, MODEL)
        self.assertEqual(rows[0]["dt"].isoformat(), "2020-01-01")

    def test_valid_product_parsing(self) -> None:
        rows = load_export(self._write([product_values()]), PRODUCT_SPEC, BATCH, MODEL)
        self.assertEqual(rows[0]["parent_asin"], "PARENT001")

    def test_exact_column_count(self) -> None:
        with self.assertRaisesRegex(ServingSyncError, "column count mismatch"):
            load_export(self._write([overview_values()[:-1]]), OVERVIEW_SPEC, BATCH, MODEL)

    def test_null_conversion(self) -> None:
        values = product_values()
        values[1] = r"\N"
        rows = load_export(self._write([values]), PRODUCT_SPEC, BATCH, MODEL)
        self.assertIsNone(rows[0]["product_title"])

    def test_utf8_product_title(self) -> None:
        rows = load_export(self._write([product_values()]), PRODUCT_SPEC, BATCH, MODEL)
        self.assertEqual(rows[0]["product_title"], "时尚连衣裙")

    def test_control_a_parsing(self) -> None:
        path = self._write([overview_values()])
        self.assertIn("\x01", path.read_text(encoding="utf-8"))
        self.assertEqual(len(load_export(path, OVERVIEW_SPEC, BATCH, MODEL)), 1)

    def test_invalid_rate_rejected(self) -> None:
        values = overview_values()
        values[7] = "1.1"
        with self.assertRaisesRegex(ServingSyncError, "rate outside"):
            load_export(self._write([values]), OVERVIEW_SPEC, BATCH, MODEL)

    def test_invalid_numeric_value_rejected(self) -> None:
        values = overview_values()
        values[2] = "not-a-number"
        with self.assertRaisesRegex(ServingSyncError, "invalid value"):
            load_export(self._write([values]), OVERVIEW_SPEC, BATCH, MODEL)

    def test_unexpected_batch_rejected(self) -> None:
        values = overview_values()
        values[0] = "other_batch"
        with self.assertRaisesRegex(ServingSyncError, "unexpected batch"):
            load_export(self._write([values]), OVERVIEW_SPEC, BATCH, MODEL)

    def test_unexpected_model_rejected(self) -> None:
        values = overview_values()
        values[1] = "other_model"
        with self.assertRaisesRegex(ServingSyncError, "unexpected model"):
            load_export(self._write([values]), OVERVIEW_SPEC, BATCH, MODEL)

    def test_duplicate_overview_key(self) -> None:
        with self.assertRaisesRegex(ServingSyncError, "duplicate primary key"):
            load_export(self._write([overview_values(), overview_values()]), OVERVIEW_SPEC, BATCH, MODEL)

    def test_duplicate_daily_key(self) -> None:
        with self.assertRaisesRegex(ServingSyncError, "duplicate primary key"):
            load_export(self._write([daily_values(), daily_values()]), DAILY_SPEC, BATCH, MODEL)

    def test_duplicate_product_key(self) -> None:
        with self.assertRaisesRegex(ServingSyncError, "duplicate primary key"):
            load_export(self._write([product_values(), product_values()]), PRODUCT_SPEC, BATCH, MODEL)

    def test_transaction_plan_generation(self) -> None:
        plan = build_transaction_plan()
        self.assertEqual(len(plan), 3)
        self.assertEqual([item["table"] for item in plan], [spec.name for spec in (OVERVIEW_SPEC, DAILY_SPEC, PRODUCT_SPEC)])

    def test_parameterized_statement_generation(self) -> None:
        insert_sql = build_insert_statement(OVERVIEW_SPEC)
        delete_sql = build_delete_statement(OVERVIEW_SPEC)
        self.assertEqual(insert_sql.count("%s"), len(OVERVIEW_SPEC.columns))
        self.assertEqual(delete_sql.count("%s"), 2)
        self.assertNotIn(BATCH, insert_sql + delete_sql)

    def test_safe_summary_without_credentials(self) -> None:
        datasets = {
            OVERVIEW_SPEC.name: [dict(zip(OVERVIEW_SPEC.columns, overview_values()))],
            DAILY_SPEC.name: [dict(zip(DAILY_SPEC.columns, daily_values()))],
            PRODUCT_SPEC.name: [dict(zip(PRODUCT_SPEC.columns, product_values()))],
        }
        totals = {
            "overview_review_count": 99703,
            "product_count": 76784,
            "positive_count": 64861,
            "neutral_count": 18943,
            "negative_count": 15899,
            "sentiment_count_sum": 99703,
            "daily_review_count_sum": 99703,
            "product_review_count_sum": 99703,
        }
        summary = make_summary(BATCH, MODEL, datasets, totals, "PENDING")
        path = self.root / "summary.json"
        write_summary_atomic(path, summary)
        serialized = path.read_text(encoding="utf-8")
        self.assertNotIn("password", serialized.lower())
        self.assertNotIn("user_id", serialized.lower())
        self.assertEqual(json.loads(serialized)["result"], "PENDING")


if __name__ == "__main__":
    unittest.main()
