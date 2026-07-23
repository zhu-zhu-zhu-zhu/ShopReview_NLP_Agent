"""Tool: get_kpi → GET /api/kpi."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, get_adapter

DESCRIPTION = (
    "获取当前导出范围内评论情感总览 KPI："
    "评论量、正/中/负数量与比率、均分。"
    "返回当前生产批次总览；可选日期参数不改变批次级快照。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_kpi",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "可选 YYYY-MM-DD；批次级快照不按日期切分",
                },
                "end_date": {
                    "type": "string",
                    "description": "可选 YYYY-MM-DD；批次级快照不按日期切分",
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    start_date = args.get("start_date")
    end_date = args.get("end_date")
    if start_date is not None:
        start_date = str(start_date).strip() or None
    if end_date is not None:
        end_date = str(end_date).strip() or None
    adapter = get_adapter()
    return as_tool_dict(adapter.get_kpi(start_date=start_date, end_date=end_date))
