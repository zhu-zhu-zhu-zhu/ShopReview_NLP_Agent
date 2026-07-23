from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.data.sync_dashboard_dws_v2_to_mysql import (
    ASPECT_RULES,
    NEGATIVE_REASON_RULES,
    DashboardSyncError,
    SPEC_BY_NAME,
    TABLE_SPECS,
    assert_no_forbidden_fields,
    build_delete_statement,
    build_insert_statement,
    confidence_bucket,
    load_export,
    match_aspects,
    match_negative_reasons,
    normalize_entity,
    sanitize_preview,
    validate_month_id,
    verified_purchase_group,
    write_manifest,
)

BATCH = "prod_v1_100k"
MODEL = "tfidf_logreg_oof_v1"


class HelpersTests(unittest.TestCase):
    def test_confidence_low_lower_boundary(self) -> None:
        self.assertEqual(confidence_bucket(0.0), "low")

    def test_confidence_medium_boundary(self) -> None:
        self.assertEqual(confidence_bucket(0.5), "medium")

    def test_confidence_high_boundary(self) -> None:
        self.assertEqual(confidence_bucket(0.75), "high")

    def test_confidence_very_high_boundaries(self) -> None:
        self.assertEqual(confidence_bucket(0.9), "very_high")
        self.assertEqual(confidence_bucket(1.0), "very_high")

    def test_confidence_rejects_invalid(self) -> None:
        with self.assertRaises(DashboardSyncError):
            confidence_bucket(1.01)

    def test_category_normalization(self) -> None:
        self.assertEqual(normalize_entity("  Fashion  "), "Fashion")
        self.assertEqual(normalize_entity(None), "Unknown")

    def test_store_normalization(self) -> None:
        self.assertEqual(normalize_entity("   "), "Unknown")

    def test_verified_purchase_grouping(self) -> None:
        self.assertEqual(verified_purchase_group(True), "verified")
        self.assertEqual(verified_purchase_group("false"), "unverified")
        self.assertEqual(verified_purchase_group(None), "unknown")

    def test_month_id_validation(self) -> None:
        self.assertTrue(validate_month_id("2024-12"))
        self.assertFalse(validate_month_id("2024-13"))
        self.assertFalse(validate_month_id("2024-1"))

    def test_preview_truncation(self) -> None:
        self.assertEqual(len(sanitize_preview("a" * 181)), 180)

    def test_preview_control_character_sanitization(self) -> None:
        preview = sanitize_preview("one\ttwo\nthree\x00four")
        self.assertNotRegex(preview, r"[\x00-\x1f]")

    def test_forbidden_user_id(self) -> None:
        with self.assertRaises(DashboardSyncError):
            assert_no_forbidden_fields(["sample_id", "user_id"])

    def test_all_serving_specs_are_safe(self) -> None:
        for spec in TABLE_SPECS:
            assert_no_forbidden_fields(spec.columns)

    def test_aspect_keyword_matching(self) -> None:
        self.assertEqual(match_aspects("Soft cotton fabric and great price"), {"material", "comfort", "price_value"})

    def test_one_review_one_aspect(self) -> None:
        self.assertEqual(match_aspects("quality quality quality"), {"quality"})

    def test_all_aspect_rules_exist(self) -> None:
        self.assertEqual(len(ASPECT_RULES), 8)

    def test_negative_reason_matching(self) -> None:
        self.assertEqual(match_negative_reasons("Poor quality and too small"), {"poor_quality", "wrong_size"})

    def test_one_review_one_reason(self) -> None:
        self.assertEqual(match_negative_reasons("refund refund return"), {"return_issue"})

    def test_all_negative_reason_rules_exist(self) -> None:
        self.assertEqual(len(NEGATIVE_REASON_RULES), 9)

    def test_parameterized_mysql_statements(self) -> None:
        spec = TABLE_SPECS[0]
        self.assertEqual(build_delete_statement(spec).count("%s"), 2)
        self.assertEqual(build_insert_statement(spec).count("%s"), len(spec.columns))
        self.assertNotIn(BATCH, build_delete_statement(spec))


class ExportContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "part-00000"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, row: list[str], repeat: int = 1) -> Path:
        self.path.write_text(("\x01".join(row) + "\n") * repeat, encoding="utf-8")
        return self.path

    @staticmethod
    def category_row() -> list[str]:
        return ["a" * 64, "Fashion", "10", "8", "4.0", "6", "2", "2", ".6", ".2", ".2", ".8", "2026-07-22 12:00:00", BATCH, MODEL]

    def test_valid_export(self) -> None:
        rows = load_export(self._write(self.category_row()), SPEC_BY_NAME["dws_category_sentiment"], BATCH, MODEL)
        self.assertEqual(rows[0]["review_count"], 10)

    def test_invalid_rate_rejection(self) -> None:
        row = self.category_row(); row[8] = "1.1"
        with self.assertRaisesRegex(DashboardSyncError, "rate outside"):
            load_export(self._write(row), SPEC_BY_NAME["dws_category_sentiment"], BATCH, MODEL)

    def test_unexpected_batch_rejection(self) -> None:
        row = self.category_row(); row[-2] = "wrong"
        with self.assertRaisesRegex(DashboardSyncError, "unexpected batch"):
            load_export(self._write(row), SPEC_BY_NAME["dws_category_sentiment"], BATCH, MODEL)

    def test_unexpected_model_rejection(self) -> None:
        row = self.category_row(); row[-1] = "wrong"
        with self.assertRaisesRegex(DashboardSyncError, "unexpected model"):
            load_export(self._write(row), SPEC_BY_NAME["dws_category_sentiment"], BATCH, MODEL)

    def test_duplicate_key_rejection(self) -> None:
        with self.assertRaisesRegex(DashboardSyncError, "duplicate primary key"):
            load_export(self._write(self.category_row(), 2), SPEC_BY_NAME["dws_category_sentiment"], BATCH, MODEL)

    def test_sentiment_reconciliation_rejection(self) -> None:
        row = self.category_row(); row[5] = "7"
        with self.assertRaisesRegex(DashboardSyncError, "sentiment count mismatch"):
            load_export(self._write(row), SPEC_BY_NAME["dws_category_sentiment"], BATCH, MODEL)

    def test_rating_matrix_reconciliation(self) -> None:
        spec = SPEC_BY_NAME["dws_rating_prediction_matrix"]
        first = ["5", "positive", "9", ".9", "2026-07-22 12:00:00", BATCH, MODEL]
        second = ["5", "neutral", "1", ".1", "2026-07-22 12:00:00", BATCH, MODEL]
        self.path.write_text("\x01".join(first) + "\n" + "\x01".join(second) + "\n", encoding="utf-8")
        self.assertEqual(len(load_export(self.path, spec, BATCH, MODEL)), 2)

    def test_rating_matrix_bad_sum_rejected(self) -> None:
        row = ["5", "positive", "9", ".9", "2026-07-22 12:00:00", BATCH, MODEL]
        with self.assertRaisesRegex(DashboardSyncError, "rates do not reconcile"):
            load_export(self._write(row), SPEC_BY_NAME["dws_rating_prediction_matrix"], BATCH, MODEL)

    def test_duplicate_alert_ids_rejected(self) -> None:
        spec = SPEC_BY_NAME["dws_sentiment_alerts"]
        row = ["b" * 64, "PRODUCT_LOW_RATING", "medium", "product", "P1", "Product", "average_rating", "2.0", "2.5", "5", "alert", "2026-07-22 12:00:00", BATCH, MODEL]
        with self.assertRaisesRegex(DashboardSyncError, "duplicate primary key"):
            load_export(self._write(row, 2), spec, BATCH, MODEL)

    def test_sample_count_per_label(self) -> None:
        spec = SPEC_BY_NAME["dws_review_samples"]
        rows = []
        for number in range(51):
            rows.append([f"{number:064x}", "P", "Title", "Fashion", "5", "positive", ".9", "safe preview", "12", "2024-01-01 00:00:00", str(number + 1), "2026-07-22 12:00:00", BATCH, MODEL])
        self.path.write_text("".join("\x01".join(row) + "\n" for row in rows), encoding="utf-8")
        with self.assertRaisesRegex(DashboardSyncError, "sample limit"):
            load_export(self.path, spec, BATCH, MODEL)

    def test_secret_free_schema_columns(self) -> None:
        all_columns = " ".join(column for spec in TABLE_SPECS for column in spec.columns).lower()
        self.assertNotIn("password", all_columns)
        self.assertNotIn("credential", all_columns)

    def test_safe_manifest_generation(self) -> None:
        from src.data.sync_dashboard_dws_v2_to_mysql import TABLE_METADATA
        counts = {name: 1 for name in TABLE_METADATA}
        manifest = Path(self.temp.name) / "manifest.md"
        write_manifest(manifest, BATCH, MODEL, counts, counts)
        text = manifest.read_text(encoding="utf-8")
        self.assertEqual(text.count("| `dws_"), 13)
        self.assertNotIn("user_id", text)

    def test_manifest_rejects_mismatch(self) -> None:
        from src.data.sync_dashboard_dws_v2_to_mysql import TABLE_METADATA
        hive = {name: 1 for name in TABLE_METADATA}
        mysql = dict(hive); mysql["dws_category_sentiment"] = 2
        with self.assertRaisesRegex(DashboardSyncError, "reconciliation"):
            write_manifest(Path(self.temp.name) / "bad.md", BATCH, MODEL, hive, mysql)


if __name__ == "__main__":
    unittest.main()
