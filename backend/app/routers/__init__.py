"""HTTP routers for stage-G metrics APIs + Stage H agent chat."""

from app.routers import (
    agent_chat,
    alerts,
    aspects,
    health,
    kpi,
    negative_reasons,
    products,
    samples,
    serving_v2,
    trend,
)

__all__ = [
    "agent_chat",
    "alerts",
    "aspects",
    "health",
    "kpi",
    "negative_reasons",
    "products",
    "samples",
    "serving_v2",
    "trend",
]
