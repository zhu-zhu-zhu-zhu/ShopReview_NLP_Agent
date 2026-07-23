"""Tool: get_alerts → GET /api/alerts (Stage G placeholder, Scheme A)."""

from __future__ import annotations

from typing import Any

from agent.adapters.http_api import HttpApiAdapter
from agent.tools.base import as_tool_dict

DESCRIPTION = (
    "查询评论/情感相关告警快照。"
    "当前 smoke 无告警数据；调用后通常得到 not_available_in_smoke。"
    "禁止编造告警列表。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_alerts",
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
    return as_tool_dict(HttpApiAdapter().get_alerts())
