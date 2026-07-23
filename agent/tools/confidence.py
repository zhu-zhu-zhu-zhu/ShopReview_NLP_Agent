"""Tool: get_prediction_confidence → GET /api/confidence."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_prediction_confidence",
        "description": (
            "查询模型预测置信度分桶、评论量、平均预测分数及各标签数量。"
            "预测概率仅表示模型置信度，不等于业务事实。"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = arguments
    return as_tool_dict(get_adapter().get_confidence())
