"""Tool: get_category_sentiment → GET /api/categories."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_category_sentiment",
        "description": "查询品类维度的评论量、商品数、平均评分及正中负情感比例。",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = arguments
    return as_tool_dict(get_adapter().get_categories())
