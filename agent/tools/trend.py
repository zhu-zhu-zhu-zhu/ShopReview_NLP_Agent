"""Tool: get_sentiment_trend → GET /api/trend."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

DESCRIPTION = (
    "查询生产 warehouse 的近 N 日评论情感趋势。"
    "返回日期、评论量、正中负比例和平均评分；禁止编造趋势。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_sentiment_trend",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "recent_days": {
                    "type": "integer",
                    "description": "最近天数，默认 365，范围 1～1000",
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    return as_tool_dict(
        get_adapter().get_trend(
            recent_days=clamp_int(args.get("recent_days"), 1, 1000, 365),
        )
    )
