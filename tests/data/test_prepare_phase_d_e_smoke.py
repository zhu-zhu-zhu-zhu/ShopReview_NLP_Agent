import json
import tempfile
import unittest
from pathlib import Path

from src.data.prepare_phase_d_e_smoke import (
    build_nlp_records, clean_review_text, collect_pairs, review_key, weak_label,
)
from src.data.prepare_ods_smoke_data import DELIMITER, convert_metadata, convert_review


class PhaseDESmokeTests(unittest.TestCase):
    def test_matching_unique_and_unmatched_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            meta = root / "meta.jsonl"; reviews = root / "reviews.jsonl"
            meta.write_text('\n'.join(json.dumps({"parent_asin": p}) for p in ["P1", "P2"]) + '\n', encoding='utf-8')
            rows = [{"parent_asin": "X"}, {"parent_asin": "P1"}, {"parent_asin": "P1"}, {"parent_asin": "P2"}]
            reviews.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
            matched, matched_meta, _ = collect_pairs(meta, reviews, target_pairs=10, meta_limit=10, review_limit=10)
            self.assertEqual([row["parent_asin"] for row in matched], ["P1", "P2"])
            self.assertEqual(len(matched_meta), 2)

    def test_review_key_reproducibility_and_change(self):
        row = {"user_id": "U", "asin": "A", "parent_asin": "P", "timestamp": 1, "title": "T", "text": "X"}
        self.assertEqual(review_key(row), review_key(dict(row)))
        self.assertNotEqual(review_key(row), review_key({**row, "text": "Y"}))

    def test_text_cleaning_and_weak_labels(self):
        self.assertEqual(clean_review_text("  a\n\tb   c  "), "a b c")
        self.assertEqual(weak_label(1), "negative")
        self.assertEqual(weak_label(3), "neutral")
        self.assertEqual(weak_label(5), "positive")

    def test_nlp_schema_has_no_user_id(self):
        review = {"user_id": "SECRET", "asin": "A", "parent_asin": "P", "timestamp": 1,
                  "title": "T", "text": "Synthetic text", "rating": 5}
        records = build_nlp_records([review], [{"main_category": "Fashion"}])
        self.assertEqual(set(records[0]), {"review_key", "review_text_clean", "rating_label", "rating", "parent_asin", "main_category"})
        self.assertNotIn("user_id", records[0])

    def test_exact_control_a_column_counts(self):
        review_line = DELIMITER.join(convert_review({}))
        metadata_line = DELIMITER.join(convert_metadata({}))
        self.assertEqual(len(review_line.split(DELIMITER)), 10)
        self.assertEqual(len(metadata_line.split(DELIMITER)), 14)


if __name__ == "__main__":
    unittest.main()
