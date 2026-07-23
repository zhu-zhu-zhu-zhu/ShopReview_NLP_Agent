import argparse
import json
import os
import random
import tempfile
import unittest
from pathlib import Path

from src.data.inspect_amazon_fashion import (
    parse_timestamp,
    run_inspection,
    update_reservoir,
)


class InspectAmazonFashionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_jsonl(self, name, lines):
        path = self.root / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def args(self, review_path, meta_path):
        return argparse.Namespace(
            review_path=review_path,
            meta_path=meta_path,
            output_json=Path("reports/profile.json"),
            output_report=Path("reports/report.md"),
            sample_dir=Path("data/sample/amazon_fashion"),
            sample_size=2,
            seed=42,
            max_review_lines=20,
            max_meta_lines=20,
            progress_every=0,
            mode="bounded",
        )

    def run_fixture(self):
        metadata = [
            json.dumps({"parent_asin": "P1", "title": "Item", "store": "TEST_STORE",
                        "price": "12.50", "average_rating": 4.5, "rating_number": 2,
                        "categories": ["Fashion"], "description": [], "features": []}),
            "", "{bad json", json.dumps(["not", "an", "object"]),
        ]
        reviews = [
            json.dumps({"rating": 5, "title": "Great", "text": "Synthetic review",
                        "asin": "A1", "parent_asin": "P1", "user_id": "U1",
                        "timestamp": 1704067200000, "helpful_vote": 0,
                        "verified_purchase": True}),
            json.dumps({"rating": 0, "title": None, "text": "", "asin": "A2",
                        "parent_asin": "P2", "user_id": None, "timestamp": "invalid",
                        "helpful_vote": "bad", "verified_purchase": False}),
            json.dumps({"rating": 5, "title": "Great", "text": "Synthetic review",
                        "asin": "A1", "parent_asin": "P1", "user_id": "U1",
                        "timestamp": 1704067200000, "helpful_vote": 0,
                        "verified_purchase": True}),
            "", "{bad json", json.dumps("not an object"),
        ]
        review_path = self.write_jsonl("reviews.jsonl", reviews)
        meta_path = self.write_jsonl("meta.jsonl", metadata)
        old_cwd = Path.cwd()
        os.chdir(self.root)
        try:
            return run_inspection(self.args(review_path, meta_path))
        finally:
            os.chdir(old_cwd)

    def test_valid_records_blank_malformed_and_non_object(self):
        profile = self.run_fixture()
        self.assertEqual(profile["review_profile"]["valid_object_count"], 3)
        self.assertEqual(profile["review_profile"]["blank_lines"], 1)
        self.assertEqual(profile["review_profile"]["malformed_json_count"], 1)
        self.assertEqual(profile["review_profile"]["non_object_json_count"], 1)
        self.assertEqual(profile["metadata_profile"]["valid_object_count"], 1)

    def test_missing_null_invalid_rating_and_timestamp(self):
        review = self.run_fixture()["review_profile"]
        self.assertEqual(review["field_null"]["title"], 1)
        self.assertEqual(review["blank_review_text_count"], 1)
        self.assertEqual(review["field_null"]["user_id"], 1)
        self.assertEqual(review["field_occurrence"].get("images", 0), 0)
        self.assertEqual(review["rating_outside_1_to_5_count"], 1)
        self.assertEqual(review["timestamp_invalid_or_missing_count"], 1)

    def test_join_matched_and_unmatched(self):
        review = self.run_fixture()["review_profile"]
        self.assertEqual(review["matched_parent_asin_rows"], 2)
        self.assertEqual(review["unmatched_parent_asin_rows"], 1)
        self.assertAlmostEqual(review["sample_parent_asin_join_rate"], 2 / 3)

    def test_bounded_physical_line_counts(self):
        profile = self.run_fixture()
        self.assertEqual(profile["review_profile"]["physical_lines_inspected"], 6)
        self.assertEqual(profile["metadata_profile"]["physical_lines_inspected"], 4)

    def test_reservoir_sample_reproducibility(self):
        first, second = [], []
        rng_first, rng_second = random.Random(42), random.Random(42)
        for count in range(1, 101):
            update_reservoir(first, {"value": count}, count, 10, rng_first)
            update_reservoir(second, {"value": count}, count, 10, rng_second)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)

    def test_timestamp_parser(self):
        parsed = parse_timestamp(1704067200000)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[1].date().isoformat(), "2024-01-01")
        self.assertIsNone(parse_timestamp("not-a-date"))

    def test_output_json_and_samples_created(self):
        self.run_fixture()
        profile_path = self.root / "reports/profile.json"
        self.assertTrue(profile_path.is_file())
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(profile["completion_status"], "successful")
        self.assertTrue((self.root / "data/sample/amazon_fashion/reviews_sample_2.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
