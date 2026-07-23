"""Tool: get_top_negative_stores → GET /api/stores."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_top_negative_stores",
        "description": (
            "返回店铺差评风险榜，按 negative_rate 等字段排序。"
            "店铺标识使用 store_key，同时返回 store_name、product_count 与评论指标。"
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
        get_adapter().get_stores(
            limit=clamp_int(args.get("limit"), 1, 20, 10),
            min_reviews=clamp_int(args.get("min_reviews"), 0, 10_000, 20),
        )
    )
