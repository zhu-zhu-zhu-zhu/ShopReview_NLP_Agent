"""Tool: get_aspect_stats → GET /api/aspects."""

from __future__ import annotations

from typing import Any

from agent.tools.base import (
    ASPECT_VOCABULARY,
    as_tool_dict,
    get_adapter,
    invalid_args,
)

DESCRIPTION = (
    "获取关键词规则方面聚合统计。"
    "aspect 使用受控英文词："
    "appearance, size_fit, comfort, material, price_value, quality, "
    "shipping_packaging, durability。"
    "可用中文解释词义，但调用本工具时 aspect 参数必须用英文受控词。"
)

OPENAI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_aspect_stats",
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "aspect": {
                    "type": "string",
                    "description": (
                        "可选过滤；必须是受控英文词之一，例如 size_fit / durability"
                    ),
                },
            },
            "additionalProperties": False,
        },
    },
}


def run(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    aspect_raw = args.get("aspect")
    aspect: str | None
    if aspect_raw is None or str(aspect_raw).strip() == "":
        aspect = None
    else:
        aspect = str(aspect_raw).strip().lower()
        if aspect not in ASPECT_VOCABULARY:
            return invalid_args(
                "aspect 必须是受控英文词之一: "
                + ", ".join(sorted(ASPECT_VOCABULARY))
                + f"；收到: {aspect_raw!r}",
                source="tool:get_aspect_stats",
            )
    adapter = get_adapter()
    return as_tool_dict(adapter.get_aspects(aspect=aspect))
