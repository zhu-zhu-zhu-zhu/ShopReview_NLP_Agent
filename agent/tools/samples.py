"""Tool: search_review_samples → GET /api/samples."""

from __future__ import annotations

from typing import Any

from agent.tools.base import as_tool_dict, clamp_int, get_adapter, invalid_args

DESCRIPTION = (
    "检索生产 warehouse 中的脱敏评论样例，只返回 review_text_preview。"
    "不返回 user_id 或完整评论，可按预测标签过滤。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_review_samples",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认 10，范围 1～20",
                },
                "pred_label": {
                    "type": "string",
                    "enum": ["negative", "neutral", "positive"],
                    "description": "可选模型预测标签",
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    label = str(args.get("pred_label") or "").lower() or None
    if label not in {None, "negative", "neutral", "positive"}:
        return invalid_args(
            "pred_label 必须是 negative/neutral/positive",
            source="tool:search_review_samples",
        )
    return as_tool_dict(
        get_adapter().get_samples(
            limit=clamp_int(args.get("limit"), 1, 20, 10),
            pred_label=label,
        )
    )
