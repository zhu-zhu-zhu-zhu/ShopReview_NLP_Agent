"""Tool: get_sentiment_trend → GET /api/trend (Stage G placeholder, Scheme A)."""

from __future__ import annotations

from typing import Any

from agent.adapters.http_api import HttpApiAdapter
from agent.tools.base import as_tool_dict

DESCRIPTION = (
    "查询评论情感日趋势/时间序列。"
    "当前 smoke 导出无日趋势数据；调用后通常得到 not_available_in_smoke。"
    "禁止编造趋势上升或下降。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_sentiment_trend",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = arguments
    # Scheme A: always hit Stage G placeholder HTTP (same as dashboard capability strip).
    return as_tool_dict(HttpApiAdapter().get_trend())
