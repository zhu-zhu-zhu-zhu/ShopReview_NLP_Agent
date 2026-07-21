import unittest

from src.data.prepare_ods_smoke_data import (
    DELIMITER,
    NULL,
    META_COLUMNS,
    REVIEW_COLUMNS,
    convert_metadata,
    convert_review,
    nested_json,
    sanitize_string,
)


class PrepareOdsSmokeDataTests(unittest.TestCase):
    def test_control_and_whitespace_sanitization(self):
        self.assertEqual(sanitize_string(f"a{DELIMITER}b\r\nc\td"), "a b  c d")

    def test_null_conversion(self):
        row = convert_review({})
        self.assertTrue(all(value == NULL for value in row))

    def test_nested_list_serialization(self):
        self.assertEqual(nested_json(["a\nb", 1]), '["a b",1]')

    def test_nested_object_serialization(self):
        self.assertEqual(nested_json({"note": f"a{DELIMITER}b"}), '{"note":"a b"}')

    def test_boolean_conversion(self):
        self.assertEqual(convert_review({"verified_purchase": True})[-1], "true")
        self.assertEqual(convert_review({"verified_purchase": False})[-1], "false")
        self.assertEqual(convert_review({"verified_purchase": None})[-1], NULL)

    def test_review_column_count(self):
        self.assertEqual(len(convert_review({})), len(REVIEW_COLUMNS))
        self.assertEqual(len(REVIEW_COLUMNS), 10)

    def test_metadata_column_count(self):
        self.assertEqual(len(convert_metadata({})), len(META_COLUMNS))
        self.assertEqual(len(META_COLUMNS), 14)


if __name__ == "__main__":
    unittest.main()
