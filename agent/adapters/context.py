"""Context flag: prefer in-process metrics when serving /api/agent/chat."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_inprocess: ContextVar[bool] = ContextVar("agent_inprocess", default=False)


def is_inprocess() -> bool:
    return bool(_inprocess.get())


@contextmanager
def inprocess_mode() -> Iterator[None]:
    token = _inprocess.set(True)
    try:
        yield
    finally:
        _inprocess.reset(token)
