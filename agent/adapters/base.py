"""Adapter interfaces and unified result shape for Agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, TypedDict


class AdapterResult(TypedDict, total=False):
    ok: bool
    data: Any
    source: str
    data_scope: str
    schema_version: str
    production_business_metrics: bool
    fetched_at: str
    error: str | None
    message: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ok_result(
    data: Any,
    *,
    source: str,
    data_scope: str = "",
    schema_version: str = "draft_v0.1",
    production_business_metrics: bool = False,
    message: str | None = None,
) -> AdapterResult:
    out: AdapterResult = {
        "ok": True,
        "data": data,
        "source": source,
        "data_scope": data_scope,
        "schema_version": schema_version,
        "production_business_metrics": production_business_metrics,
        "fetched_at": utc_now_iso(),
        "error": None,
        "message": message,
    }
    return out


def fail_result(
    error: str,
    *,
    source: str = "",
    message: str | None = None,
    data_scope: str = "",
    schema_version: str = "draft_v0.1",
    production_business_metrics: bool = False,
) -> AdapterResult:
    return {
        "ok": False,
        "data": None,
        "source": source,
        "data_scope": data_scope,
        "schema_version": schema_version,
        "production_business_metrics": production_business_metrics,
        "fetched_at": utc_now_iso(),
        "error": error,
        "message": message,
    }


class MetricsAdapter(ABC):
    """Fetch Stage-G metrics for Agent tools (HTTP or local smoke JSON)."""

    @abstractmethod
    def get_health(self) -> AdapterResult: ...

    @abstractmethod
    def get_kpi(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AdapterResult: ...

    @abstractmethod
    def get_top_negative_products(
        self,
        limit: int = 5,
        min_reviews: int = 1,
    ) -> AdapterResult: ...

    @abstractmethod
    def get_aspects(self, aspect: str | None = None) -> AdapterResult: ...

    @abstractmethod
    def get_negative_reasons(
        self,
        limit: int = 10,
        parent_asin: str | None = None,
    ) -> AdapterResult: ...

    @abstractmethod
    def get_trend(self) -> AdapterResult: ...

    @abstractmethod
    def get_alerts(self) -> AdapterResult: ...

    @abstractmethod
    def get_samples(self) -> AdapterResult: ...
