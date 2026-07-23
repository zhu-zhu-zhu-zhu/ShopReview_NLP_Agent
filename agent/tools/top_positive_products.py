"""Tool: get_top_positive_products → GET /api/top-positive-products."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_top_positive_products",
        "description": (
            "按 positive_rate、positive_count、review_count 降序返回商品好评榜。"
            "商品主键必须使用 parent_asin。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "返回条数，默认 5，范围 1～20"},
                "min_reviews": {"type": "integer", "description": "最少评论数，默认 5"},
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    return as_tool_dict(
        get_adapter().get_top_positive_products(
            limit=clamp_int(args.get("limit"), 1, 20, 5),
            min_reviews=clamp_int(args.get("min_reviews"), 0, 10_000, 5),
        )
    )
