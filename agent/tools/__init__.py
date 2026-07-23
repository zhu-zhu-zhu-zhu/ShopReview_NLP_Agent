"""Tool registry: handlers + OpenAI function-calling schemas."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from agent.adapters.base import fail_result
from agent.tools import (
    alerts,
    aspects,
    kpi,
    negative_reasons,
    samples,
    top_negative,
    trend,
)
from agent.tools.base import append_tool_log, summarize_for_step

TOOL_HANDLERS: dict[str, Callable[[dict[str, Any] | None], dict[str, Any]]] = {
    "get_kpi": kpi.run,
    "get_top_negative_products": top_negative.run,
    "get_aspect_stats": aspects.run,
    "get_negative_reasons": negative_reasons.run,
    "get_sentiment_trend": trend.run,
    "get_alerts": alerts.run,
    "search_review_samples": samples.run,
}

_OPENAI_SCHEMAS: list[dict[str, Any]] = [
    kpi.OPENAI_SCHEMA,
    top_negative.OPENAI_SCHEMA,
    aspects.OPENAI_SCHEMA,
    negative_reasons.OPENAI_SCHEMA,
    trend.OPENAI_SCHEMA,
    alerts.OPENAI_SCHEMA,
    samples.OPENAI_SCHEMA,
]


def openai_tools() -> list[dict[str, Any]]:
    """Chat Completions / compatible ``tools`` array for the LLM client."""
    return list(_OPENAI_SCHEMAS)


def run_tool(name: str, arguments: dict[str, Any] | str | None = None) -> dict[str, Any]:
    """Execute a whitelist tool by name. Unknown names → ok=false."""
    args: dict[str, Any]
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
            if not isinstance(parsed, dict):
                result = dict(
                    fail_result(
                        "invalid_args",
                        source=f"tool:{name}",
                        message="arguments JSON 根节点必须是 object",
                    )
                )
                append_tool_log(name, {}, result)
                return result
            args = parsed
        except json.JSONDecodeError:
            result = dict(
                fail_result(
                    "invalid_args",
                    source=f"tool:{name}",
                    message="arguments 不是合法 JSON object",
                )
            )
            append_tool_log(name, {}, result)
            return result
    elif isinstance(arguments, dict):
        args = arguments
    else:
        args = {}

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        result = dict(
            fail_result(
                "unknown_tool",
                source=f"tool:{name}",
                message=f"未知工具: {name}；可用: {', '.join(sorted(TOOL_HANDLERS))}",
            )
        )
        append_tool_log(name, args, result)
        return result

    result = handler(args)
    if not isinstance(result, dict):
        result = dict(
            fail_result(
                "internal_error",
                source=f"tool:{name}",
                message="工具返回非 dict",
            )
        )
    append_tool_log(name, args, result)
    return result


def tool_names() -> list[str]:
    return sorted(TOOL_HANDLERS.keys())


__all__ = [
    "TOOL_HANDLERS",
    "openai_tools",
    "run_tool",
    "summarize_for_step",
    "tool_names",
]
