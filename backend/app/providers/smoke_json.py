from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.providers.base import MetricsProvider, ProviderError

REQUIRED_SMOKE_FILES = (
    "manifest.json",
    "sentiment_overview.json",
    "product_sentiment.json",
    "aspect_summary.json",
    "negative_reasons.json",
)


class SmokeJsonProvider(MetricsProvider):
    """Read Phase F safe JSON exports (smoke / contract data)."""

    def __init__(self, export_dir: Path, data_mode: str = "smoke") -> None:
        self.export_dir = export_dir
        self.data_mode = data_mode
        self._ensure_files()

    def _ensure_files(self) -> None:
        if not self.export_dir.is_dir():
            raise ProviderError(
                f"Smoke export directory not found: {self.export_dir}",
                error="upstream_unavailable",
            )
        missing = [
            name
            for name in REQUIRED_SMOKE_FILES
            if not (self.export_dir / name).is_file()
        ]
        if missing:
            raise ProviderError(
                f"Missing smoke files: {', '.join(missing)}",
                error="upstream_unavailable",
            )

    def _load(self, filename: str) -> dict[str, Any]:
        path = self.export_dir / filename
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderError(
                f"Failed to read {filename}: {exc}",
                error="upstream_unavailable",
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderError(
                f"Invalid smoke payload in {filename}: expected object",
                error="upstream_unavailable",
            )
        return payload

    def dataset_meta(self, filename: str) -> dict[str, Any]:
        payload = self._load(filename)
        return {
            "schema_version": str(payload.get("schema_version") or "draft_v0.1"),
            "data_scope": str(payload.get("data_scope") or ""),
            "source": f"smoke:{filename}",
            "production_business_metrics": False,
            "data_mode": self.data_mode,
        }

    def response_meta(self, source: str, *, data_scope: str = "") -> dict[str, Any]:
        return {
            "data_mode": self.data_mode,
            "schema_version": "draft_v0.1",
            "data_scope": data_scope,
            "production_business_metrics": False,
            "source": source,
        }

    def get_health_meta(self) -> dict[str, Any]:
        manifest = self._load("manifest.json")
        overview = self._load("sentiment_overview.json")
        aspects = self._load("aspect_summary.json")
        sentiment_scope = str(overview.get("data_scope") or "")
        aspect_scope = str(aspects.get("data_scope") or "")
        scopes = [part for part in (sentiment_scope, aspect_scope) if part]
        summary = " + ".join(dict.fromkeys(scopes)) if scopes else "smoke"
        return {
            "ok": True,
            "data_mode": self.data_mode,
            "schema_version": str(manifest.get("schema_version") or "draft_v0.1"),
            "production_business_metrics": bool(
                manifest.get("production_business_metrics", False)
            ),
            "export_name": str(manifest.get("export_name") or ""),
            "data_scope_summary": summary,
            "sentiment_data": str(manifest.get("sentiment_data") or ""),
            "aspect_data": str(manifest.get("aspect_data") or ""),
            "record_counts": manifest.get("record_counts") or {},
            "source": "smoke:manifest.json",
        }

    def get_kpi(self) -> dict[str, Any]:
        payload = self._load("sentiment_overview.json")
        records = payload.get("records") or []
        if not records:
            raise ProviderError(
                "sentiment_overview.json has no records",
                error="upstream_unavailable",
            )
        row = dict(records[0])
        if not row.get("data_scope"):
            row["data_scope"] = payload.get("data_scope")
        return row

    def get_top_negative_products(
        self, limit: int, min_reviews: int
    ) -> list[dict[str, Any]]:
        payload = self._load("product_sentiment.json")
        records = [dict(item) for item in (payload.get("records") or [])]
        filtered = [
            item
            for item in records
            if float(item.get("review_count") or 0) >= min_reviews
        ]
        filtered.sort(
            key=lambda item: (
                float(item.get("negative_rate") or 0.0),
                float(item.get("negative_count") or 0.0),
                float(item.get("review_count") or 0.0),
            ),
            reverse=True,
        )
        return filtered[:limit]

    def get_aspects(self, aspect: str | None) -> list[dict[str, Any]]:
        payload = self._load("aspect_summary.json")
        records = [dict(item) for item in (payload.get("records") or [])]
        if aspect:
            target = aspect.strip().lower()
            records = [
                item
                for item in records
                if str(item.get("aspect") or "").strip().lower() == target
            ]
        return records

    def get_negative_reasons(
        self, limit: int, parent_asin: str | None
    ) -> list[dict[str, Any]]:
        payload = self._load("negative_reasons.json")
        records = [dict(item) for item in (payload.get("records") or [])]
        if parent_asin:
            target = parent_asin.strip()
            records = [
                item
                for item in records
                if str(item.get("parent_asin") or "").strip() == target
            ]
        records.sort(
            key=lambda item: (
                float(item.get("reason_count") or 0.0),
                float(item.get("reason_share") or 0.0),
            ),
            reverse=True,
        )
        return records[:limit]

    def get_trend(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        recent_days: int | None = None,
    ) -> list[dict[str, Any]]:
        _ = start_date, end_date, limit, recent_days
        raise ProviderError(
            "当前为 smoke 快照，无日趋势/时间序列数据",
            error="not_available_in_smoke",
        )

    def get_monthly_trend(self) -> list[dict[str, Any]]:
        raise ProviderError(
            "当前为 smoke 快照，无月趋势数据",
            error="not_available_in_smoke",
        )

    def get_categories(self) -> list[dict[str, Any]]:
        raise ProviderError(
            "当前为 smoke 快照，无品类汇总",
            error="not_available_in_smoke",
        )

    def get_stores(
        self, limit: int = 10, min_reviews: int = 20
    ) -> list[dict[str, Any]]:
        _ = limit, min_reviews
        raise ProviderError(
            "当前为 smoke 快照，无店铺汇总",
            error="not_available_in_smoke",
        )

    def get_verified_purchase(self) -> list[dict[str, Any]]:
        raise ProviderError(
            "当前为 smoke 快照，无认证购买对比",
            error="not_available_in_smoke",
        )

    def get_rating_matrix(self) -> list[dict[str, Any]]:
        raise ProviderError(
            "当前为 smoke 快照，无星级×预测矩阵",
            error="not_available_in_smoke",
        )

    def get_confidence(self) -> list[dict[str, Any]]:
        raise ProviderError(
            "当前为 smoke 快照，无置信度分桶",
            error="not_available_in_smoke",
        )

    def get_alerts(
        self,
        *,
        limit: int = 20,
        alert_level: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = limit, alert_level
        raise ProviderError(
            "当前为 smoke 快照，无告警数据",
            error="not_available_in_smoke",
        )

    def get_samples(
        self,
        *,
        limit: int = 20,
        pred_label: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = limit, pred_label
        raise ProviderError(
            "当前为 smoke 安全导出，不含评论文本样例",
            error="not_available_in_smoke",
        )
