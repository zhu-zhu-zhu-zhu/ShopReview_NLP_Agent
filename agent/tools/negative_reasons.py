"""Tool: get_negative_reasons → GET /api/negative-reasons."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter

DESCRIPTION = (
    "查询当前生产批次的全局差评原因分布。"
    "结果来自 keyword_rules_v1，不可归因到单个 parent_asin，也不是 LLM 抽取。"
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
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    limit = clamp_int(args.get("limit"), 1, 50, 10)
    adapter = get_adapter()
    return as_tool_dict(adapter.get_negative_reasons(limit=limit))
