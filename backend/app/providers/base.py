from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MetricsProvider(ABC):
    """Data access boundary for dashboard / Agent APIs."""

    @abstractmethod
    def get_health_meta(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_kpi(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_top_negative_products(
        self, limit: int, min_reviews: int
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_aspects(self, aspect: str | None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_negative_reasons(
        self, limit: int, parent_asin: str | None
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_trend(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        recent_days: int | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("trend not available for this provider")

    def get_monthly_trend(self) -> list[dict[str, Any]]:
        raise NotImplementedError("monthly trend not available for this provider")

    def get_categories(self) -> list[dict[str, Any]]:
        raise NotImplementedError("categories not available for this provider")

    def get_stores(
        self, limit: int = 10, min_reviews: int = 20
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("stores not available for this provider")

    def get_verified_purchase(self) -> list[dict[str, Any]]:
        raise NotImplementedError("verified purchase not available for this provider")

    def get_rating_matrix(self) -> list[dict[str, Any]]:
        raise NotImplementedError("rating matrix not available for this provider")

    def get_confidence(self) -> list[dict[str, Any]]:
        raise NotImplementedError("confidence not available for this provider")

    def get_alerts(
        self,
        *,
        limit: int = 20,
        alert_level: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("alerts not available for this provider")

    def get_samples(
        self,
        *,
        limit: int = 20,
        pred_label: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("samples not available for this provider")

    def response_meta(self, source: str, *, data_scope: str = "") -> dict[str, Any]:
        return {
            "data_mode": "unknown",
            "schema_version": "draft_v0.1",
            "data_scope": data_scope,
            "production_business_metrics": False,
            "source": source,
        }


class ProviderError(Exception):
    """Upstream read / validation failure."""

    def __init__(self, message: str, *, error: str = "upstream_unavailable") -> None:
        super().__init__(message)
        self.message = message
        self.error = error
