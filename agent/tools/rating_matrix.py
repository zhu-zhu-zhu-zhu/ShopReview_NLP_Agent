"""Tool: get_rating_prediction_matrix → GET /api/rating-matrix."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_rating_prediction_matrix",
        "description": (
            "查询星级与模型预测标签交叉矩阵，用于判断一星/五星与"
            "negative、neutral、positive 预测的方向一致性。"
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
    return as_tool_dict(get_adapter().get_rating_matrix())
