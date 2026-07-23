"""Tool: get_top_negative_products → GET /api/top-negative-products."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

DESCRIPTION = (
    "按负面率等排序返回差评商品列表。"
    "商品主键为 parent_asin（不是 product_id）。"
    "smoke 小样本下 min_reviews 建议为 1。"
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
                    "description": "最少评论数过滤；smoke 默认 1",
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
