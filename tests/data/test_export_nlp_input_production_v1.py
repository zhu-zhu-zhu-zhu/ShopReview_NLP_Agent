import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.data.export_nlp_input_production_v1 import (
    EXPECTED_FIELDS,
    file_sha256,
    validate_existing,
    validate_record,
    write_export,
)


def valid_record(key="a" * 64, text="Synthetic review", **changes):
    record = {
        "review_key": key,
        "review_text_clean": text,
        "rating_label": "positive",
        "rating": 5.0,
        "parent_asin": "P1",
        "main_category": "AMAZON FASHION",
        "review_time": "2023-01-01 00:00:00",
        "load_batch_id": "prod_v1_100k",
    }
    record.update(changes)
    return record


class ProductionNlpExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.output = root / "input.jsonl"
        self.summary = root / "summary.json"
        self.manifest = root / "manifest.json"

    def tearDown(self):
        self.temp.cleanup()

    def export(self, records):
        return write_export(
            records, self.output, self.summary, self.manifest,
            generated_at_utc="2026-01-01T00:00:00Z",
        )

    def test_valid_output_schema(self):
        self.export([valid_record()])
        record = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(tuple(record), EXPECTED_FIELDS)

    def test_missing_review_key_rejected(self):
        record = valid_record(); del record["review_key"]
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_record(record, "prod_v1_100k")

    def test_blank_review_text_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-blank"):
            validate_record(valid_record(text="  "), "prod_v1_100k")

    def test_invalid_rating_label_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid"):
            validate_record(valid_record(rating_label="predicted"), "prod_v1_100k")

    def test_duplicate_review_key_detected(self):
        with self.assertRaisesRegex(ValueError, "duplicate review_key"):
            self.export([valid_record(), valid_record(text="Another synthetic review")])
        self.assertFalse(self.output.exists())

    def test_user_id_field_rejected(self):
        record = valid_record(user_id="SECRET")
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_record(record, "prod_v1_100k")

    def test_utf8_review_text_preserved(self):
        self.export([valid_record(text="尺码合适，面料舒适")])
        record = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(record["review_text_clean"], "尺码合适，面料舒适")
        self.assertIn("尺码合适", self.output.read_text(encoding="utf-8"))

    def test_deterministic_field_order(self):
        self.export([valid_record()])
        line = self.output.read_text(encoding="utf-8").strip()
        positions = [line.index(f'"{field}"') for field in EXPECTED_FIELDS]
        self.assertEqual(positions, sorted(positions))

    def test_sha256_generation(self):
        self.output.write_bytes(b"abc\n")
        self.assertEqual(file_sha256(self.output), hashlib.sha256(b"abc\n").hexdigest())

    def test_summary_reconciliation(self):
        summary = self.export([
            valid_record(key="a" * 64, rating_label="negative", rating=1.0),
            valid_record(key="b" * 64, rating_label="neutral", rating=3.0),
            valid_record(key="c" * 64, rating_label="positive", rating=5.0),
        ])
        checked = validate_existing(
            self.output, self.summary, self.manifest, expected_row_count=3,
        )
        self.assertEqual(checked, summary)
        self.assertEqual((summary["negative_count"], summary["neutral_count"], summary["positive_count"]), (1, 1, 1))
        self.assertEqual(summary["unique_review_key_count"], 3)


if __name__ == "__main__":
    unittest.main()
