"""In-process adapter — call Stage G providers without nested HTTP (avoids deadlock)."""

from __future__ import annotations

from typing import Any

from agent.adapters.base import AdapterResult, MetricsAdapter, fail_result, ok_result


class InProcessAdapter(MetricsAdapter):
    """Used when orchestrator runs inside the FastAPI process (AGENT chat route)."""

    def _provider(self) -> Any:
        from app.providers import get_provider

        return get_provider()

    def _meta_from_provider(self, filename: str) -> dict[str, Any]:
        provider = self._provider()
        if hasattr(provider, "dataset_meta"):
            return provider.dataset_meta(filename)
        return {
            "schema_version": "draft_v0.1",
            "data_scope": "",
            "source": f"inprocess:{filename}",
            "production_business_metrics": False,
            "data_mode": "smoke",
        }

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
            result = self._ok(row, filename="sentiment_overview.json", source="inprocess:kpi")
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
                filename="product_sentiment.json",
                source="inprocess:top-negative-products",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:top-negative-products",
                message=str(exc),
            )

    def get_aspects(self, aspect: str | None = None) -> AdapterResult:
        try:
            rows = self._provider().get_aspects(aspect)
            return self._ok(
                rows,
                filename="aspect_summary.json",
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
        parent_asin: str | None = None,
    ) -> AdapterResult:
        try:
            rows = self._provider().get_negative_reasons(limit, parent_asin)
            return self._ok(
                rows,
                filename="negative_reasons.json",
                source="inprocess:negative-reasons",
            )
        except Exception as exc:  # noqa: BLE001
            return fail_result(
                "upstream_unavailable",
                source="inprocess:negative-reasons",
                message=str(exc),
            )

    def get_trend(self) -> AdapterResult:
        return fail_result(
            "not_available_in_smoke",
            source="inprocess:trend",
            message="当前为 smoke 快照，无日趋势/时间序列数据",
        )

    def get_alerts(self) -> AdapterResult:
        return fail_result(
            "not_available_in_smoke",
            source="inprocess:alerts",
            message="当前为 smoke 快照，无告警快照数据",
        )

    def get_samples(self) -> AdapterResult:
        return fail_result(
            "not_available_in_smoke",
            source="inprocess:samples",
            message="当前为 smoke 安全导出，不含评论文本样例",
        )
