"""LLM-to-tools orchestrator for production investigations."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from agent.config import get_settings
from agent.llm.client import LLMClient, LLMError
from agent.tools import openai_tools, run_tool
from agent.tools.base import summarize_for_step

logger = logging.getLogger("shopreview.agent.orchestrator")

_METRIC_HINT = re.compile(
    r"(多少|比率|负面|正面|中性|KPI|kpi|排行|排名|方面|原因|周报|均分|评论量|"
    r"商品|店铺|告警|趋势|星级|矩阵|置信|购买|品类|批次|模型版本)",
    re.I,
)

_FORCE_TOOL_HINT = (
    "你必须先调用白名单工具获取真实数据后再回答；"
    "不要凭记忆编造数字。请立即发起 tool call。"
)


def _load_system_prompt() -> str:
    path = Path(__file__).resolve().parent / "prompts" / "system.md"
    return path.read_text(encoding="utf-8")


def _assistant_message_from_raw(raw: Any) -> dict[str, Any]:
    """Convert SDK message object into an OpenAI-compatible dict for history."""
    if raw is None:
        return {"role": "assistant", "content": None}
    tool_calls = getattr(raw, "tool_calls", None)
    content = getattr(raw, "content", None)
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        serialized = []
        for tc in tool_calls:
            fn = getattr(tc, "function", None)
            serialized.append(
                {
                    "id": getattr(tc, "id", ""),
                    "type": "function",
                    "function": {
                        "name": getattr(fn, "name", "") if fn else "",
                        "arguments": getattr(fn, "arguments", "{}") if fn else "{}",
                    },
                }
            )
        msg["tool_calls"] = serialized
    return msg


def chat(question: str, session_id: str | None = None) -> dict[str, Any]:
    """Run one Agent turn. ``session_id`` reserved for future multi-turn."""
    _ = session_id
    settings = get_settings()
    q = (question or "").strip()
    if not q:
        return {
            "ok": False,
            "answer": "问题不能为空。",
            "steps": [],
            "mode": "llm",
            "data_mode": settings.data_mode,
            "error": "invalid_args",
        }

    steps: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _load_system_prompt()},
        {"role": "user", "content": q},
    ]

    try:
        llm = LLMClient(settings)
    except LLMError as exc:
        return {
            "ok": False,
            "answer": f"大模型未就绪：{exc.message}",
            "steps": [],
            "mode": "llm",
            "data_mode": settings.data_mode,
            "error": exc.code,
        }

    tools = openai_tools()
    max_steps = max(1, settings.max_steps)
    forced_once = False

    try:
        for round_i in range(max_steps):
            tool_choice: str | dict[str, Any] = "auto"
            if forced_once and round_i == 1:
                tool_choice = "required"

            resp = llm.chat(messages, tools=tools, tool_choice=tool_choice)

            if resp.tool_calls:
                messages.append(_assistant_message_from_raw(resp.raw))
                for call in resp.tool_calls:
                    args = call.arguments
                    if args.get("_parse_error"):
                        result = {
                            "ok": False,
                            "error": "invalid_args",
                            "message": "模型返回的 tool arguments 不是合法 JSON",
                            "data": None,
                            "source": f"tool:{call.name}",
                        }
                    else:
                        result = run_tool(call.name, args)
                    steps.append(
                        {
                            "tool": call.name,
                            "args": {k: v for k, v in args.items() if not str(k).startswith("_")},
                            "ok": bool(result.get("ok")),
                            "summary": summarize_for_step(call.name, result),
                            "source": result.get("source") or f"tool:{call.name}",
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                continue

            answer = (resp.content or "").strip()
            needs_tools = bool(_METRIC_HINT.search(q))
            if needs_tools and not steps and not forced_once:
                forced_once = True
                messages.append({"role": "user", "content": _FORCE_TOOL_HINT})
                logger.info("Force tool retry for metric-like question")
                continue

            return {
                "ok": True,
                "answer": answer or "（模型未返回文本）",
                "steps": steps,
                "mode": "llm",
                "data_mode": settings.data_mode,
                "error": None,
            }

        # max steps exhausted
        summaries = "; ".join(s["summary"] for s in steps) if steps else "无"
        return {
            "ok": False,
            "answer": (
                "已达到最大工具步数，请缩小问题范围。"
                f"已查询到的工具摘要：{summaries}"
            ),
            "steps": steps,
            "mode": "llm",
            "data_mode": settings.data_mode,
            "error": "max_steps_exceeded",
        }
    except LLMError as exc:
        return {
            "ok": False,
            "answer": f"大模型调用失败：{exc.message}",
            "steps": steps,
            "mode": "llm",
            "data_mode": settings.data_mode,
            "error": exc.code,
        }
