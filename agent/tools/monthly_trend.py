"""Tool: get_monthly_sentiment_trend → GET /api/trends/monthly."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_monthly_sentiment_trend",
        "description": (
            "查询最近若干个月的情感聚合趋势，包含 month_id、评论量和正中负比例。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最近月份数，默认 24，范围 1～60"},
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    return as_tool_dict(
        get_adapter().get_monthly_trend(
            limit=clamp_int(args.get("limit"), 1, 60, 24),
        )
    )
