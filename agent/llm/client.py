"""OpenAI-compatible LLM client (DeepSeek / others)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from agent.config import Settings, get_settings

logger = logging.getLogger("shopreview.agent.llm")


class LLMError(Exception):
    """Raised when the upstream LLM call fails."""

    def __init__(self, message: str, *, code: str = "llm_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None


class LLMClient:
    """Thin wrapper around OpenAI SDK pointed at DeepSeek (or any compatible API)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.llm_api_key:
            raise LLMError(
                "未配置 LLM_API_KEY。请在 agent/.env 中设置。",
                code="llm_config_error",
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError(
                "缺少 openai 包。请执行: pip install openai",
                code="llm_config_error",
            ) from exc

        base = self.settings.llm_base_url or "https://api.deepseek.com"
        self.model = self.settings.llm_model or "deepseek-v4-flash"
        self.timeout = getattr(self.settings, "llm_timeout_sec", 60.0)
        self._client = OpenAI(
            api_key=self.settings.llm_api_key,
            base_url=base,
            timeout=self.timeout,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        tool_choice: str | dict[str, Any] | None = "auto",
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.settings.temperature,
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

        t0 = time.perf_counter()
        try:
            completion = self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — normalize vendor errors
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning("LLM call failed model=%s latency_ms=%s err=%s", self.model, latency_ms, type(exc).__name__)
            raise LLMError(str(exc), code="llm_error") from exc

        latency_ms = int((time.perf_counter() - t0) * 1000)
        choice = completion.choices[0].message
        tool_calls = self._parse_tool_calls(choice.tool_calls)
        content = choice.content if choice.content else None
        logger.info(
            "LLM ok model=%s latency_ms=%s tool_calls=%s content_len=%s",
            self.model,
            latency_ms,
            [tc.name for tc in tool_calls],
            len(content or ""),
        )
        return LLMResponse(content=content, tool_calls=tool_calls, raw=choice)

    @staticmethod
    def _parse_tool_calls(raw_calls: Any) -> list[ToolCall]:
        if not raw_calls:
            return []
        out: list[ToolCall] = []
        for call in raw_calls:
            fn = getattr(call, "function", None)
            name = getattr(fn, "name", "") if fn else ""
            arg_raw = getattr(fn, "arguments", "{}") if fn else "{}"
            args: dict[str, Any]
            if isinstance(arg_raw, dict):
                args = arg_raw
            else:
                try:
                    parsed = json.loads(arg_raw or "{}")
                    args = parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    args = {"_raw": arg_raw, "_parse_error": True}
            out.append(
                ToolCall(
                    id=str(getattr(call, "id", "") or f"call_{len(out)}"),
                    name=str(name),
                    arguments=args,
                )
            )
        return out
