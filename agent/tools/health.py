"""Tool: get_data_health → GET /api/health."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, get_adapter

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_data_health",
        "description": (
            "查询当前数据模式、生产指标标志、load_batch_id、model_version、"
            "服务库表行数和数据来源。用于回答数据血缘、批次、模型版本与后端状态。"
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
    return as_tool_dict(get_adapter().get_health())
