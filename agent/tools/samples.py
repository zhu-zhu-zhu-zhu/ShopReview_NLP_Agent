"""Tool: search_review_samples → GET /api/samples (Stage G placeholder, Scheme A)."""

from __future__ import annotations

from typing import Any

from agent.adapters.http_api import HttpApiAdapter
from agent.tools.base import as_tool_dict

DESCRIPTION = (
    "检索脱敏评论文本样例。"
    "当前 smoke 安全导出不含原文；调用后通常得到 not_available_in_smoke。"
    "禁止从原始 JSONL 自行取评论文本。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_review_samples",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "可选关键词；smoke 下接口仍不可用",
                },
                "limit": {
                    "type": "integer",
                    "description": "可选条数；smoke 下接口仍不可用",
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = arguments  # Stage G /api/samples 暂无查询参数；保留 schema 供将来扩展
    return as_tool_dict(HttpApiAdapter().get_samples())
