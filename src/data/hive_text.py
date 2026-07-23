"""Amazon Fashion JSON-to-Hive text conversion primitives."""

from __future__ import annotations

import json
import math
from typing import Any


DELIMITER = "\x01"
NULL = r"\N"


def sanitize_string(value: str) -> str:
    return value.replace(DELIMITER, " ").replace("\r", " ").replace("\n", " ").replace("\t", " ")


def sanitize_nested(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, list):
        return [sanitize_nested(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_nested(item) for key, item in value.items()}
    return value


def nested_json(value: Any) -> str:
    if value is None:
        return NULL
    return json.dumps(sanitize_nested(value), ensure_ascii=False, separators=(",", ":"))


def string_value(value: Any) -> str:
    if value is None:
        return NULL
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, (list, dict)):
        return nested_json(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return sanitize_string(str(value))


def number_value(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return NULL
    if isinstance(value, (int, float)):
        number = float(value)
        return str(value) if math.isfinite(number) else NULL
    if isinstance(value, str):
        cleaned = value.strip()
        try:
            number = float(cleaned)
        except ValueError:
            return NULL
        return cleaned if math.isfinite(number) else NULL
    return NULL


def integer_value(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return NULL
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return str(int(value))
    if isinstance(value, str):
        try:
            return str(int(value.strip()))
        except ValueError:
            return NULL
    return NULL


def boolean_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return NULL


def raw_price_value(value: Any) -> str:
    if value is None:
        return NULL
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, (list, dict)):
        return nested_json(value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def convert_review(obj: dict[str, Any]) -> list[str]:
    return [
        number_value(obj.get("rating")),
        string_value(obj.get("title")),
        string_value(obj.get("text")),
        nested_json(obj.get("images")),
        string_value(obj.get("asin")),
        string_value(obj.get("parent_asin")),
        string_value(obj.get("user_id")),
        integer_value(obj.get("timestamp")),
        integer_value(obj.get("helpful_vote")),
        boolean_value(obj.get("verified_purchase")),
    ]


def convert_metadata(obj: dict[str, Any]) -> list[str]:
    return [
        string_value(obj.get("main_category")),
        string_value(obj.get("title")),
        number_value(obj.get("average_rating")),
        integer_value(obj.get("rating_number")),
        nested_json(obj.get("features")),
        nested_json(obj.get("description")),
        raw_price_value(obj.get("price")),
        nested_json(obj.get("images")),
        nested_json(obj.get("videos")),
        string_value(obj.get("store")),
        nested_json(obj.get("categories")),
        nested_json(obj.get("details")),
        string_value(obj.get("parent_asin")),
        nested_json(obj.get("bought_together")),
    ]
