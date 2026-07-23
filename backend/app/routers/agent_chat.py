"""POST /api/agent/chat — production LLM Agent entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Ensure repo root is importable when uvicorn uses --app-dir backend
_REPO_ROOT = Path(__file__).resolve().parents[3]
_root_str = str(_REPO_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

from agent.config import reset_settings_cache  # noqa: E402
from agent.adapters.context import inprocess_mode  # noqa: E402
from agent.orchestrator import chat as agent_chat  # noqa: E402

router = APIRouter(tags=["agent"])


class ChatRequest(BaseModel):
    question: str = Field(..., description="User question")
    session_id: str | None = Field(default=None, description="Optional session id")


@router.post("/api/agent/chat")
def agent_chat_endpoint(body: ChatRequest) -> dict[str, Any]:
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": "invalid_args",
                "message": "question 不能为空",
            },
        )
    # Reload env in case agent/.env changed while server runs
    reset_settings_cache()
    # In-process metrics: nested HTTP to the same uvicorn process can 502/deadlock.
    with inprocess_mode():
        result = agent_chat(question, session_id=body.session_id)
    return result
