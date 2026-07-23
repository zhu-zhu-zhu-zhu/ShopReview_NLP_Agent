"""Tool: get_top_negative_products → GET /api/top-negative-products."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

DESCRIPTION = (
    "按负面率等排序返回差评商品列表。"
    "商品主键为 parent_asin（不是 product_id）。"
    "支持使用最少评论数过滤低样本商品。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_top_negative_products",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认 5，范围 1～20",
                },
                "min_reviews": {
                    "type": "integer",
                    "description": "最少评论数过滤",
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    limit = clamp_int(args.get("limit"), 1, 20, 5)
    min_reviews = clamp_int(args.get("min_reviews"), 1, 10_000, 1)
    adapter = get_adapter()
    return as_tool_dict(
        adapter.get_top_negative_products(limit=limit, min_reviews=min_reviews)
    )
