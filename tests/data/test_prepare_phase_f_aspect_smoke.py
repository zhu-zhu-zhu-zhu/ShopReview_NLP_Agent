import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.data.export_phase_f_agent_json import TABLE_SPECS, build_export_payload, validate_export_payload
from src.data.prepare_phase_f_aspect_smoke import DELIMITER, REQUIRED_FIELDS, load_fixture, to_control_a, validate_records


def valid_record():
    return {
        "review_key": "a" * 64,
        "aspect": "size",
        "reason_code": "too_small",
        "reason_name": "Too small",
        "aspect_sentiment": "negative",
        "confidence": 0.9,
        "extractor_version": "synthetic_test_v1",
        "extracted_at": "2026-07-21T09:00:00Z",
    }


class PhaseFAspectSmokeTests(unittest.TestCase):
    def test_valid_aspect_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.json"
            path.write_text(json.dumps([valid_record()]), encoding="utf-8")
            records = load_fixture(path)
        self.assertEqual(records, [valid_record()])

    def test_invalid_aspect_rejected(self):
        record = {**valid_record(), "aspect": "sleeve"}
        with self.assertRaisesRegex(ValueError, "invalid aspect"):
            validate_records([record])

    def test_invalid_sentiment_rejected(self):
        record = {**valid_record(), "aspect_sentiment": "mixed"}
        with self.assertRaisesRegex(ValueError, "invalid aspect_sentiment"):
            validate_records([record])

    def test_confidence_outside_range_rejected(self):
        for confidence in (-0.01, 1.01):
            with self.subTest(confidence=confidence), self.assertRaisesRegex(ValueError, "confidence"):
                validate_records([{**valid_record(), "confidence": confidence}])

    def test_duplicate_contract_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate aspect contract key"):
            validate_records([valid_record(), copy.deepcopy(valid_record())])

    def test_missing_required_field_rejected(self):
        record = valid_record()
        del record["reason_name"]
        with self.assertRaisesRegex(ValueError, "missing required"):
            validate_records([record])

    def test_unknown_field_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown field"):
            validate_records([{**valid_record(), "review_text": "must not pass"}])

    def test_control_a_conversion(self):
        line = to_control_a(validate_records([valid_record()])).rstrip("\n")
        self.assertEqual(len(line.split(DELIMITER)), len(REQUIRED_FIELDS))
        self.assertEqual(len(REQUIRED_FIELDS), 8)

    def test_json_export_schema_validation(self):
        spec = TABLE_SPECS["sentiment_overview"]
        record = {
            "review_count": 1,
            "user_count": 1,
            "product_count": 1,
            "positive_count": 1,
            "neutral_count": 0,
            "negative_count": 0,
            "positive_rate": 1.0,
            "neutral_rate": 0.0,
            "negative_rate": 0.0,
            "average_rating": 5.0,
            "generated_at": "2026-07-21 09:00:00",
            "data_scope": "phase_d_e_smoke_contract",
        }
        payload = build_export_payload("sentiment_overview", spec, [record])
        validate_export_payload(payload, "sentiment_overview", spec)
        payload["records"][0]["user_id"] = "forbidden"
        with self.assertRaises(ValueError):
            validate_export_payload(payload, "sentiment_overview", spec)


if __name__ == "__main__":
    unittest.main()
