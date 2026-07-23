"""Shared helpers for production Agent tools."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.adapters.base import AdapterResult, MetricsAdapter, fail_result
from agent.adapters.http_api import HttpApiAdapter
from agent.config import get_settings, repo_root

ASPECT_VOCABULARY = frozenset(
    {
        "appearance",
        "size_fit",
        "comfort",
        "material",
        "price_value",
        "quality",
        "shipping_packaging",
        "durability",
    }
)


def clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_adapter() -> MetricsAdapter:
    settings = get_settings()
    # Serving /api/agent/chat: avoid nested HTTP to the same uvicorn worker.
    from agent.adapters.context import is_inprocess

    if is_inprocess():
        from agent.adapters.inprocess import InProcessAdapter

        return InProcessAdapter()
    return HttpApiAdapter(settings)


def summarize_for_step(tool: str, result: dict[str, Any] | AdapterResult) -> str:
    if not result.get("ok"):
        err = result.get("error") or "error"
        msg = result.get("message") or ""
        return f"ok=false error={err}" + (f" {msg[:80]}" if msg else "")

    data = result.get("data")
    if tool == "get_kpi" and isinstance(data, dict):
        return (
            f"review_count={data.get('review_count')}, "
            f"negative_rate={data.get('negative_rate')}, "
            f"average_rating={data.get('average_rating')}"
        )
    if tool in {
        "get_top_negative_products",
        "get_top_positive_products",
    } and isinstance(data, list):
        head = data[0].get("parent_asin") if data and isinstance(data[0], dict) else None
        return f"n={len(data)}" + (f", top={head}" if head else "")
    if tool in {
        "get_top_negative_stores",
        "get_top_positive_stores",
    } and isinstance(data, list):
        head = data[0].get("store_name") if data and isinstance(data[0], dict) else None
        return f"n={len(data)}" + (f", top={head}" if head else "")
    if tool == "get_aspect_stats" and isinstance(data, list):
        return f"n={len(data)}"
    if tool == "get_negative_reasons" and isinstance(data, list):
        return f"n={len(data)}"
    if tool == "get_data_health" and isinstance(data, dict):
        return (
            f"data_mode={data.get('data_mode')}, "
            f"batch={data.get('load_batch_id')}, "
            f"model={data.get('model_version')}"
        )
    if isinstance(data, list):
        return f"n={len(data)}"
    if isinstance(data, dict):
        return f"keys={len(data)}"
    return "ok=true"


def append_tool_log(tool: str, args: dict[str, Any], result: dict[str, Any]) -> None:
    """Best-effort JSONL log under agent/logs/ (never logs secrets)."""
    try:
        log_dir = repo_root() / "agent" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / "tools.jsonl"
        row = {
            "ts": now_iso(),
            "tool": tool,
            "args": args,
            "ok": result.get("ok"),
            "error": result.get("error"),
            "source": result.get("source"),
            "summary": summarize_for_step(tool, result),
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        return


def as_tool_dict(result: AdapterResult) -> dict[str, Any]:
    """Normalize AdapterResult to a plain dict for LLM / run_tool."""
    return dict(result)


def invalid_args(message: str, *, source: str = "tool") -> dict[str, Any]:
    return dict(
        fail_result(
            "invalid_args",
            source=source,
            message=message,
        )
    )
