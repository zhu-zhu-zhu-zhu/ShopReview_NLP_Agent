"""Smoke JSON adapter — optional (Stage H3). Not implemented in H0."""

from __future__ import annotations

from agent.adapters.base import AdapterResult, MetricsAdapter, fail_result


class SmokeJsonAdapter(MetricsAdapter):
    """Placeholder until H3. Prefer HttpApiAdapter for H0/H1."""

    def _nyi(self, name: str) -> AdapterResult:
        return fail_result(
            "not_implemented",
            source=f"smoke:{name}",
            message="SmokeJsonAdapter 将在步骤 H3 实现；当前请使用 AGENT_DATA_MODE=http",
        )

    def get_health(self) -> AdapterResult:
        return self._nyi("health")

    def get_kpi(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AdapterResult:
        return self._nyi("kpi")

    def get_top_negative_products(
        self,
        limit: int = 5,
        min_reviews: int = 1,
    ) -> AdapterResult:
        return self._nyi("top_negative_products")

    def get_aspects(self, aspect: str | None = None) -> AdapterResult:
        return self._nyi("aspects")

    def get_negative_reasons(
        self,
        limit: int = 10,
        parent_asin: str | None = None,
    ) -> AdapterResult:
        return self._nyi("negative_reasons")

    def get_trend(self) -> AdapterResult:
        return self._nyi("trend")

    def get_alerts(self) -> AdapterResult:
        return self._nyi("alerts")

    def get_samples(self) -> AdapterResult:
        return self._nyi("samples")
