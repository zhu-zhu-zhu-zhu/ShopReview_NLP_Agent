"""Tool: get_negative_reasons → GET /api/negative-reasons."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

DESCRIPTION = (
    "获取商品 × 差评原因明细列表。"
    "可用 parent_asin 过滤单一商品；主键为 parent_asin。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_negative_reasons",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认 10，范围 1～50",
                },
                "parent_asin": {
                    "type": "string",
                    "description": "可选，按商品族主键过滤",
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    limit = clamp_int(args.get("limit"), 1, 50, 10)
    parent_raw = args.get("parent_asin")
    parent_asin = (
        None
        if parent_raw is None or str(parent_raw).strip() == ""
        else str(parent_raw).strip()
    )
    adapter = get_adapter()
    return as_tool_dict(
        adapter.get_negative_reasons(limit=limit, parent_asin=parent_asin)
    )
