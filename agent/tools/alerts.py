"""Tool: get_alerts → GET /api/alerts."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter, invalid_args

DESCRIPTION = (
    "查询生产评论情感告警，可按 CRITICAL、HIGH、MEDIUM、LOW 过滤。"
    "返回告警实体、指标、阈值和告警信息；禁止编造告警。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_alerts",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认 20，范围 1～50",
                },
                "alert_level": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "可选告警等级",
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    level = str(args.get("alert_level") or "").upper() or None
    if level not in {None, "CRITICAL", "HIGH", "MEDIUM", "LOW"}:
        return invalid_args(
            "alert_level 必须是 CRITICAL/HIGH/MEDIUM/LOW",
            source="tool:get_alerts",
        )
    return as_tool_dict(
        get_adapter().get_alerts(
            limit=clamp_int(args.get("limit"), 1, 50, 20),
            alert_level=level,
        )
    )
