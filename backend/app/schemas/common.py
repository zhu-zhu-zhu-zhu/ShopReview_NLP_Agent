from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    data_mode: str
    schema_version: str = "draft_v0.1"
    data_scope: str = ""
    production_business_metrics: bool = False
    source: str
    message: str | None = None


class OkResponse(BaseModel):
    ok: bool = True
    data: Any
    meta: ResponseMeta


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)
