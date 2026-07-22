from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.nlp.train_tfidf_logreg_v1 import (
    InputValidationError,
    basic_metrics,
    build_pipeline,
    generate_oof_predictions,
    load_input_jsonl,
    sha256_file,
    stratified_split_indices,
)
from src.nlp.validate_prediction_output import (
    PREDICTION_FIELDS,
    PredictionValidationError,
    validate_predictions,
)


def input_row(index: int, label: str = "positive") -> dict[str, object]:
    prefix = {"negative": "bad broken awful", "neutral": "average okay item", "positive": "great excellent love"}[label]
    return {
        "review_key": f"key-{index:04d}",
        "review_text_clean": f"{prefix} token{index}",
        "rating_label": label,
        "rating": 5.0,
        "parent_asin": "PARENT",
        "main_category": "AMAZON FASHION",
        "review_time": "2020-01-01 00:00:00",
        "load_batch_id": "prod_v1_100k",
    }


def prediction_row(key: str, label: str = "positive") -> dict[str, object]:
    scores = {"negative": 0.1, "neutral": 0.2, "positive": 0.7}
    return {
        "review_key": key,
        "pred_label": label,
        "pred_score": scores.get(label, 0.7),
        "negative_score": scores["negative"],
        "neutral_score": scores["neutral"],
        "positive_score": scores["positive"],
        "model_version": "tfidf_logreg_oof_v1",
        "inferred_at": "2026-01-01T00:00:00Z",
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class InputAndPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _load_rows(self, rows: list[dict[str, object]]):
        path = self.root / "input.jsonl"
        write_jsonl(path, rows)
        return load_input_jsonl(path, sha256_file(path), len(rows))

    def test_valid_input_jsonl(self) -> None:
        keys, texts, labels, profile = self._load_rows([input_row(1)])
        self.assertEqual(keys, ["key-0001"])
        self.assertEqual(len(texts), 1)
        self.assertEqual(labels, ["positive"])
        self.assertEqual(profile["row_count"], 1)

    def test_hash_validation(self) -> None:
        path = self.root / "input.jsonl"
        write_jsonl(path, [input_row(1)])
        with self.assertRaisesRegex(InputValidationError, "SHA-256 mismatch"):
            load_input_jsonl(path, "0" * 64, 1)

    def test_duplicate_input_review_key(self) -> None:
        row = input_row(1)
        with self.assertRaisesRegex(InputValidationError, "duplicate review_key"):
            self._load_rows([row, dict(row)])

    def test_blank_text_rejection(self) -> None:
        row = input_row(1)
        row["review_text_clean"] = "  "
        with self.assertRaisesRegex(InputValidationError, "blank review_text_clean"):
            self._load_rows([row])

    def test_invalid_label_rejection(self) -> None:
        row = input_row(1)
        row["rating_label"] = "mixed"
        with self.assertRaisesRegex(InputValidationError, "invalid rating_label"):
            self._load_rows([row])

    def test_deterministic_stratified_split(self) -> None:
        labels = [label for label in ("negative", "neutral", "positive") for _ in range(10)]
        first = stratified_split_indices(labels, 42)
        second = stratified_split_indices(labels, 42)
        self.assertEqual(first, second)
        self.assertEqual([len(part) for part in first], [24, 3, 3])
        self.assertEqual({labels[index] for index in first[2]}, set(labels))

    def test_pipeline_training_on_synthetic_text(self) -> None:
        texts, labels = self._synthetic_training_data()
        model = build_pipeline(1.0, 42, 100, 1, 1.0, 2, 100)
        model.fit(texts, labels)
        self.assertEqual(set(model.predict(texts)), set(labels))

    def test_predict_proba_output(self) -> None:
        texts, labels = self._synthetic_training_data()
        model = build_pipeline(1.0, 42, 100, 1, 1.0, 2, 100)
        model.fit(texts, labels)
        probabilities = model.predict_proba(["great love"])
        self.assertEqual(probabilities.shape, (1, 3))
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=7)

    @staticmethod
    def _synthetic_training_data() -> tuple[list[str], list[str]]:
        labels = [label for label in ("negative", "neutral", "positive") for _ in range(10)]
        rows = [input_row(index, label) for index, label in enumerate(labels)]
        return [str(row["review_text_clean"]) for row in rows], [str(row["rating_label"]) for row in rows]


class PredictionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.jsonl"
        write_jsonl(self.source, [input_row(1), input_row(2)])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _validate(self, rows: list[dict[str, object]]):
        path = self.root / "predictions.jsonl"
        write_jsonl(path, rows)
        return validate_predictions(self.source, path, "tfidf_logreg_oof_v1", 2)

    def test_predicted_score_consistency(self) -> None:
        summary = self._validate([prediction_row("key-0001"), prediction_row("key-0002")])
        self.assertEqual(summary["result"], "PASS")

    def test_invalid_prediction_label(self) -> None:
        with self.assertRaisesRegex(PredictionValidationError, "invalid pred_label"):
            self._validate([prediction_row("key-0001", "mixed"), prediction_row("key-0002")])

    def test_duplicate_prediction_key(self) -> None:
        with self.assertRaisesRegex(PredictionValidationError, "duplicate prediction"):
            self._validate([prediction_row("key-0001"), prediction_row("key-0001")])

    def test_probability_sum_validation(self) -> None:
        row = prediction_row("key-0001")
        row["negative_score"] = 0.4
        with self.assertRaisesRegex(PredictionValidationError, "probability sum"):
            self._validate([row, prediction_row("key-0002")])

    def test_forbidden_review_text_rejected(self) -> None:
        row = prediction_row("key-0001")
        row["review_text"] = "must not be exported"
        with self.assertRaises(PredictionValidationError):
            self._validate([row, prediction_row("key-0002")])

    def test_forbidden_user_id_rejected(self) -> None:
        row = prediction_row("key-0001")
        row["user_id"] = "forbidden"
        with self.assertRaises(PredictionValidationError):
            self._validate([row, prediction_row("key-0002")])

    def test_deterministic_field_order(self) -> None:
        self.assertEqual(tuple(prediction_row("key-0001")), PREDICTION_FIELDS)

    def test_safe_summary_generation(self) -> None:
        summary = self._validate([prediction_row("key-0001"), prediction_row("key-0002")])
        serialized = json.dumps(summary)
        self.assertNotIn("review_text", serialized)
        self.assertNotIn("user_id", serialized)
        self.assertEqual(summary["unique_key_count"], 2)

    def test_oof_predictions_preserve_order_and_coverage(self) -> None:
        labels = [label for label in ("negative", "neutral", "positive") for _ in range(10)]
        rows = [input_row(index, label) for index, label in enumerate(labels)]
        source = self.root / "oof_source.jsonl"
        output = self.root / "oof_predictions.jsonl"
        write_jsonl(source, rows)
        details, warning_rows = generate_oof_predictions(
            output,
            [str(row["review_key"]) for row in rows],
            [str(row["review_text_clean"]) for row in rows],
            [str(row["rating_label"]) for row in rows],
            1.0,
            "tfidf_logreg_oof_v1",
            "2026-01-01T00:00:00Z",
            42,
            100,
            1,
            1.0,
            2,
            100,
        )
        summary = validate_predictions(source, output, "tfidf_logreg_oof_v1", 30)
        output_keys = [json.loads(line)["review_key"] for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(output_keys, [row["review_key"] for row in rows])
        self.assertEqual(summary["coverage"], 1.0)
        self.assertFalse(details["source_row_used_in_own_fold_training"])
        self.assertIsInstance(warning_rows, list)


if __name__ == "__main__":
    unittest.main()
