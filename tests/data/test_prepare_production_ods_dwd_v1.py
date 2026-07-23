import json
import tempfile
import unittest
from pathlib import Path

from src.data.hive_text import DELIMITER, NULL
from src.data.prepare_production_ods_dwd_v1 import (
    META_OUTPUT, MISSING_OUTPUT, REVIEW_OUTPUT, SUMMARY_OUTPUT, prepare,
)


def write_lines(path, values):
    path.write_text("".join(value + "\n" for value in values), encoding="utf-8")


def review(parent, index=1, **changes):
    value = {
        "rating": 5, "title": f"Title {index}", "text": f"Text {index}", "images": [],
        "asin": f"A{index}", "parent_asin": parent, "user_id": f"U{index}",
        "timestamp": 1000 * index, "helpful_vote": 0, "verified_purchase": True,
    }
    value.update(changes)
    return value


def metadata(parent, title="Product", **changes):
    value = {
        "main_category": "Fashion", "title": title, "average_rating": 4.5,
        "rating_number": 10, "features": ["soft"], "description": ["desc"],
        "price": 9.99, "images": [], "videos": [], "store": "Store",
        "categories": ["Fashion"], "details": {"color": "blue"},
        "parent_asin": parent, "bought_together": None,
    }
    value.update(changes)
    return value


class ProductionV1PreparationTests(unittest.TestCase):
    def run_case(self, reviews, metadata_rows, limit=2, output_name="out"):
        root = Path(self.temp.name)
        review_path = root / "reviews.jsonl"
        meta_path = root / "meta.jsonl"
        write_lines(review_path, [item if isinstance(item, str) else json.dumps(item) for item in reviews])
        write_lines(meta_path, [item if isinstance(item, str) else json.dumps(item) for item in metadata_rows])
        output = root / output_name
        summary = prepare(
            review_path, meta_path, output, review_limit=limit, batch_id="test_batch",
            progress_every=0, generated_at_utc="2026-01-01T00:00:00+00:00",
        )
        return output, summary

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp.cleanup()

    def test_review_limit_and_metadata_extraction(self):
        output, summary = self.run_case(
            [review("P1", 1), review("P2", 2), review("P3", 3)],
            [metadata("P3"), metadata("P2"), metadata("P1")],
        )
        self.assertEqual(summary["valid_reviews_selected"], 2)
        self.assertEqual(summary["physical_review_lines_scanned"], 2)
        self.assertEqual(summary["matched_metadata_count"], 2)
        self.assertEqual(len((output / REVIEW_OUTPUT).read_text(encoding="utf-8").splitlines()), 2)

    def test_malformed_blank_and_non_object_reviews_are_counted(self):
        _, summary = self.run_case(
            ["", "{bad", json.dumps([1, 2]), review("P1", 1), review("P2", 2)],
            [metadata("P1"), metadata("P2")],
        )
        self.assertEqual(summary["blank_review_lines"], 1)
        self.assertEqual(summary["malformed_review_lines"], 2)
        self.assertEqual(summary["physical_review_lines_scanned"], 5)

    def test_duplicate_metadata_keeps_first_occurrence(self):
        output, summary = self.run_case(
            [review("P1", 1), review("P2", 2)],
            [metadata("P1", "First"), metadata("P1", "Second"), metadata("P2", "Third")],
        )
        rows = (output / META_OUTPUT).read_text(encoding="utf-8").splitlines()
        self.assertEqual(summary["matched_metadata_count"], 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].split(DELIMITER)[1], "First")

    def test_missing_metadata_tracking(self):
        output, summary = self.run_case(
            [review("P1", 1), review("P2", 2)], [metadata("P1")],
        )
        self.assertEqual(summary["missing_metadata_parent_asin_count"], 1)
        self.assertEqual((output / MISSING_OUTPUT).read_text(encoding="utf-8"), "P2\n")

    def test_sanitization_nested_json_nulls_and_column_counts(self):
        output, _ = self.run_case(
            [review("P1", 1, title="a\x01b", text="line1\nline2\tend")],
            [metadata("P1", features=["x\ny"], description=None, details={"a": "b\t c"})],
            limit=1,
        )
        review_line = (output / REVIEW_OUTPUT).read_text(encoding="utf-8").rstrip("\n")
        meta_line = (output / META_OUTPUT).read_text(encoding="utf-8").rstrip("\n")
        review_fields = review_line.split(DELIMITER)
        meta_fields = meta_line.split(DELIMITER)
        self.assertEqual(len(review_fields), 10)
        self.assertEqual(len(meta_fields), 14)
        self.assertEqual(review_fields[1], "a b")
        self.assertEqual(review_fields[2], "line1 line2 end")
        self.assertEqual(json.loads(meta_fields[4]), ["x y"])
        self.assertEqual(meta_fields[5], NULL)
        self.assertEqual(json.loads(meta_fields[11]), {"a": "b  c"})

    def test_deterministic_outputs(self):
        reviews = [review("P2", 1), review("P1", 2)]
        meta_rows = [metadata("P1", "One"), metadata("P2", "Two")]
        first, first_summary = self.run_case(reviews, meta_rows, output_name="first")
        second, second_summary = self.run_case(reviews, meta_rows, output_name="second")
        self.assertEqual(first_summary, second_summary)
        for name in (REVIEW_OUTPUT, META_OUTPUT, MISSING_OUTPUT, SUMMARY_OUTPUT):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
