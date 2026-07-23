"""Metrics adapters for Stage H Agent."""

from agent.adapters.base import AdapterResult, MetricsAdapter, fail_result, ok_result
from agent.adapters.http_api import HttpApiAdapter

__all__ = [
    "AdapterResult",
    "HttpApiAdapter",
    "MetricsAdapter",
    "fail_result",
    "ok_result",
]
