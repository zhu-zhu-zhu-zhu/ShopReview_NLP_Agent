"""Call the production provider in-process without nested HTTP."""

from __future__ import annotations

from typing import Any

from agent.adapters.base import AdapterResult, MetricsAdapter, fail_result, ok_result


class InProcessAdapter(MetricsAdapter):
    """Used when orchestrator runs inside the FastAPI process (AGENT chat route)."""

    def _provider(self) -> Any:
        from app.providers import get_provider

        return get_provider()

    def _meta_from_provider(self, source_name: str) -> dict[str, Any]:
        provider = self._provider()
        return provider.response_meta(f"warehouse:{source_name}")

    def _ok(self, data: Any, *, filename: str, source: str) -> AdapterResult:
        meta = self._meta_from_provider(filename)
        return ok_result(
            data,
            source=source,
            data_scope=str(meta.get("data_scope") or ""),
            schema_version=str(meta.get("schema_version") or "draft_v0.1"),
            production_business_metrics=bool(
                meta.get("production_business_metrics", False)
            ),
        )

    def get_health(self) -> AdapterResult:
        try:
            meta = self._provider().get_health_meta()
            return ok_result(
                meta,
                source="inprocess:health",
                data_scope=str(meta.get("data_scope_summary") or ""),
                schema_version=str(meta.get("schema_version") or "draft_v0.1"),
                production_business_metrics=bool(
                    meta.get("production_business_metrics", False)
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:health",
                message=str(exc),
            )

    def get_kpi(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AdapterResult:
        try:
            row = self._provider().get_kpi()
            result = self._ok(row, filename="dws_sentiment_overview", source="inprocess:kpi")
            if start_date and end_date:
                result["message"] = (
                    "当前为快照数据，不支持时间窗过滤；已忽略 start_date/end_date"
                )
            return result
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:kpi",
                message=str(exc),
            )

    def get_top_negative_products(
        self,
        limit: int = 5,
        min_reviews: int = 1,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_top_negative_products(limit, min_reviews)
            return self._ok(
                rows,
                filename="dws_product_sentiment",
                source="inprocess:top-negative-products",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:top-negative-products",
                message=str(exc),
            )

    def get_top_positive_products(
        self,
        limit: int = 5,
        min_reviews: int = 5,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_top_positive_products(limit, min_reviews)
            return self._ok(
                rows,
                filename="dws_product_sentiment",
                source="inprocess:top-positive-products",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:top-positive-products",
                message=str(exc),
            )

    def get_aspects(self, aspect: str | None = None) -> AdapterResult:
        try:
            rows = self._provider().get_aspects(aspect)
            return self._ok(
                rows,
                filename="dws_aspect_summary",
                source="inprocess:aspects",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:aspects",
                message=str(exc),
            )

    def get_negative_reasons(
        self,
        limit: int = 10,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_negative_reasons(limit, None)
            return self._ok(
                rows,
                filename="dws_negative_reason_summary",
                source="inprocess:negative-reasons",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:negative-reasons",
                message=str(exc),
            )

    def get_trend(self, recent_days: int = 365) -> AdapterResult:
        try:
            rows = self._provider().get_trend(recent_days=recent_days)
            return self._ok(
                rows,
                filename="dws_sentiment_daily",
                source="inprocess:trend",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:trend",
                message=str(exc),
            )

    def get_monthly_trend(self, limit: int = 24) -> AdapterResult:
        try:
            rows = self._provider().get_monthly_trend()
            rows = rows[-limit:]
            return self._ok(
                rows,
                filename="dws_monthly_sentiment",
                source="inprocess:monthly-trend",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:monthly-trend",
                message=str(exc),
            )

    def get_categories(self) -> AdapterResult:
        try:
            rows = self._provider().get_categories()
            return self._ok(
                rows,
                filename="dws_category_sentiment",
                source="inprocess:categories",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:categories",
                message=str(exc),
            )

    def get_stores(
        self,
        limit: int = 10,
        min_reviews: int = 20,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_stores(limit, min_reviews)
            return self._ok(
                rows,
                filename="dws_store_sentiment",
                source="inprocess:stores",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:stores",
                message=str(exc),
            )

    def get_top_positive_stores(
        self,
        limit: int = 10,
        min_reviews: int = 20,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_top_positive_stores(limit, min_reviews)
            return self._ok(
                rows,
                filename="dws_store_sentiment",
                source="inprocess:top-positive-stores",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:top-positive-stores",
                message=str(exc),
            )

    def get_verified_purchase(self) -> AdapterResult:
        try:
            rows = self._provider().get_verified_purchase()
            return self._ok(
                rows,
                filename="dws_verified_purchase_sentiment",
                source="inprocess:verified-purchase",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:verified-purchase",
                message=str(exc),
            )

    def get_rating_matrix(self) -> AdapterResult:
        try:
            rows = self._provider().get_rating_matrix()
            return self._ok(
                rows,
                filename="dws_rating_prediction_matrix",
                source="inprocess:rating-matrix",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:rating-matrix",
                message=str(exc),
            )

    def get_confidence(self) -> AdapterResult:
        try:
            rows = self._provider().get_confidence()
            return self._ok(
                rows,
                filename="dws_prediction_confidence",
                source="inprocess:confidence",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:confidence",
                message=str(exc),
            )

    def get_alerts(
        self,
        limit: int = 20,
        alert_level: str | None = None,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_alerts(
                limit=limit,
                alert_level=alert_level,
            )
            return self._ok(
                rows,
                filename="dws_sentiment_alerts",
                source="inprocess:alerts",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:alerts",
                message=str(exc),
            )

    def get_samples(
        self,
        limit: int = 10,
        pred_label: str | None = None,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_samples(
                limit=limit,
                pred_label=pred_label,
            )
            return self._ok(
                rows,
                filename="dws_review_samples",
                source="inprocess:samples",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:samples",
                message=str(exc),
            )
