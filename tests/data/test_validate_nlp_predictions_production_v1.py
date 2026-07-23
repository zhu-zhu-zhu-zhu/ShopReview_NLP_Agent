import json
import tempfile
import unittest
from pathlib import Path

from src.data.prepare_nlp_predictions_for_hive import convert_predictions, prediction_columns
from src.data.hive_text import DELIMITER, NULL
from src.data.validate_nlp_predictions_production_v1 import (
    SOURCE_TABLE,
    validate_prediction_file,
)


MODEL_VERSION = "fashion_sentiment_v1"


def prediction(key="K1", **changes):
    value = {
        "review_key": key,
        "pred_label": "positive",
        "pred_score": 0.9,
        "model_version": MODEL_VERSION,
        "inferred_at": "2026-07-21T12:00:00Z",
    }
    value.update(changes)
    return value


class ProductionPredictionValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({
            "batch_id": "prod_v1_100k",
            "source_table": SOURCE_TABLE,
            "field_order": ["review_key"],
        }), encoding="utf-8")
        self.case_number = 0

    def tearDown(self):
        self.temp.cleanup()

    def validate(self, lines, keys=("K1",), allow_partial=True, minimum_coverage=0.0):
        self.case_number += 1
        path = self.root / f"predictions_{self.case_number}.jsonl"
        path.write_text("".join(
            (line if isinstance(line, str) else json.dumps(line, ensure_ascii=False)) + "\n"
            for line in lines
        ), encoding="utf-8")
        return validate_prediction_file(
            path, self.manifest, self.root / f"state_{self.case_number}.sqlite",
            "prod_v1_100k", MODEL_VERSION,
            allow_partial=allow_partial, minimum_coverage=minimum_coverage,
            known_keys=keys,
        )

    def test_valid_prediction_record(self):
        summary = self.validate([prediction()])
        self.assertEqual(summary["validation_status"], "PASS")
        self.assertEqual(summary["valid_prediction_row_count"], 1)

    def test_malformed_json(self):
        summary = self.validate(["{bad"])
        self.assertEqual(summary["malformed_json_count"], 1)
        self.assertEqual(summary["validation_status"], "FAIL")

    def test_missing_review_key(self):
        record = prediction(); del record["review_key"]
        summary = self.validate([record])
        self.assertEqual(summary["missing_required_field_count"], 1)
        self.assertEqual(summary["validation_status"], "FAIL")

    def test_invalid_label(self):
        summary = self.validate([prediction(pred_label="unknown")])
        self.assertEqual(summary["invalid_label_count"], 1)

    def test_invalid_score(self):
        summary = self.validate([prediction(pred_score=1.1)])
        self.assertEqual(summary["invalid_score_count"], 1)

    def test_duplicate_review_key_model_version(self):
        summary = self.validate([prediction(), prediction(pred_score=0.8)])
        self.assertEqual(summary["duplicate_count"], 1)
        self.assertEqual(summary["validation_status"], "FAIL")

    def test_blank_model_version(self):
        summary = self.validate([prediction(model_version="")])
        self.assertEqual(summary["blank_model_version_count"], 1)

    def test_invalid_inferred_at(self):
        summary = self.validate([prediction(inferred_at="2026-07-21 12:00:00")])
        self.assertEqual(summary["invalid_timestamp_count"], 1)

    def test_forbidden_user_id_field(self):
        summary = self.validate([prediction(user_id="not-allowed")])
        self.assertEqual(summary["forbidden_field_count"], 1)

    def test_forbidden_review_text_field(self):
        summary = self.validate([prediction(review_text="not-allowed")])
        self.assertEqual(summary["forbidden_field_count"], 1)

    def test_partial_coverage_calculation(self):
        summary = self.validate([prediction("K1")], keys=("K1", "K2"), minimum_coverage=0.5)
        self.assertEqual(summary["coverage_rate"], 0.5)
        self.assertEqual(summary["missing_key_count"], 1)
        self.assertEqual(summary["validation_status"], "PASS")

    def test_full_coverage_calculation(self):
        summary = self.validate(
            [prediction("K1"), prediction("K2", pred_label="negative")],
            keys=("K1", "K2"), allow_partial=False, minimum_coverage=1.0,
        )
        self.assertEqual(summary["coverage_rate"], 1.0)
        self.assertEqual(summary["missing_key_count"], 0)
        self.assertEqual(summary["validation_status"], "PASS")

    def test_deterministic_control_a_conversion(self):
        source = self.root / "convert.jsonl"
        source.write_text(json.dumps(prediction(), ensure_ascii=False) + "\n", encoding="utf-8")
        first = self.root / "first.txt"; second = self.root / "second.txt"
        convert_predictions(source, first, self.root / "first_summary.json", "prod_v1_100k", MODEL_VERSION)
        convert_predictions(source, second, self.root / "second_summary.json", "prod_v1_100k", MODEL_VERSION)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(len(first.read_text(encoding="utf-8").rstrip("\n").split(DELIMITER)), 9)

    def test_optional_class_score_fields(self):
        record = prediction(negative_score=0.1, neutral_score=0.2, positive_score=0.7)
        columns = prediction_columns(record, "prod_v1_100k")
        self.assertEqual(columns[3:6], ["0.1", "0.2", "0.7"])
        without_optional = prediction_columns(prediction(), "prod_v1_100k")
        self.assertEqual(without_optional[3:6], [NULL, NULL, NULL])

    def test_safe_summary_generation(self):
        summary = self.validate([prediction("PRIVATE_KEY_VALUE")], keys=("PRIVATE_KEY_VALUE",))
        serialized = json.dumps(summary)
        self.assertNotIn("PRIVATE_KEY_VALUE", serialized)
        self.assertNotIn("user_id", serialized)
        self.assertNotIn("review_text", serialized)
        self.assertNotIn("not-allowed", serialized)


if __name__ == "__main__":
    unittest.main()
