"""Tool: get_top_positive_stores → GET /api/top-positive-stores."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_top_positive_stores",
        "description": (
            "按 positive_rate、positive_count、review_count 降序返回店铺好评榜。"
            "店铺标识使用 store_key。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "返回条数，默认 10，范围 1～20"},
                "min_reviews": {"type": "integer", "description": "最少评论数，默认 20"},
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    return as_tool_dict(
        get_adapter().get_top_positive_stores(
            limit=clamp_int(args.get("limit"), 1, 20, 10),
            min_reviews=clamp_int(args.get("min_reviews"), 0, 10_000, 20),
        )
    )
