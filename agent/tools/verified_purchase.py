"""Tool: get_verified_purchase_sentiment → GET /api/verified-purchase."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_verified_purchase_sentiment",
        "description": "比较已验证购买与未验证购买的评论量、平均评分和正中负情感比例。",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = arguments
    return as_tool_dict(get_adapter().get_verified_purchase())
