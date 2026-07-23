from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings
from app.db.mysql import MysqlReadClient
from app.providers.base import MetricsProvider, ProviderError

_V2_TABLES = (
    "dws_sentiment_overview",
    "dws_sentiment_daily",
    "dws_product_sentiment",
    "dws_category_sentiment",
    "dws_store_sentiment",
    "dws_verified_purchase_sentiment",
    "dws_rating_prediction_matrix",
    "dws_prediction_confidence",
    "dws_monthly_sentiment",
    "dws_sentiment_alerts",
    "dws_review_samples",
    "dws_aspect_summary",
    "dws_negative_reasons",
)


class WarehouseProvider(MetricsProvider):
    """Production metrics from MySQL serving DB v2 (Hive DWS sync, read-only)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.mysql_user.strip().lower() == "root":
            raise ProviderError(
                "Refusing to use MySQL root; set MYSQL_USER=agent_reader",
                error="invalid_args",
            )
        self.client = MysqlReadClient(self.settings)
        self._batch = self.settings.warehouse_load_batch_id
        self._model = self.settings.warehouse_model_version
        self._scope = self.settings.warehouse_data_scope

    def response_meta(self, source: str, *, data_scope: str = "") -> dict[str, Any]:
        return {
            "data_mode": "warehouse",
            "schema_version": "serving_v2",
            "data_scope": data_scope or self._scope,
            "production_business_metrics": True,
            "source": source,
            "load_batch_id": self._batch,
            "model_version": self._model,
            "serving_release": "prod_v2",
        }

    def _partition_params(self) -> dict[str, str]:
        return {
            "load_batch_id": self._batch,
            "model_version": self._model,
        }

    def _count(self, table: str) -> int:
        # table names are fixed allowlist — never interpolate user input
        if table not in _V2_TABLES:
            raise ProviderError(f"Unknown table {table}", error="invalid_args")
        params = self._partition_params()
        if table == "dws_sentiment_alerts":
            sql = f"""
                SELECT COUNT(*) AS n FROM {table}
                WHERE load_batch_id = %(load_batch_id)s
                  AND model_version = %(model_version)s
            """
        else:
            sql = f"""
                SELECT COUNT(*) AS n FROM {table}
                WHERE load_batch_id = %(load_batch_id)s
                  AND model_version = %(model_version)s
            """
        return int(self.client.fetch_value(sql, params) or 0)

    def get_health_meta(self) -> dict[str, Any]:
        params = self._partition_params()
        counts = {name.replace("dws_", ""): self._count(name) for name in _V2_TABLES}
        kpi = self.client.fetch_one(
            """
            SELECT review_count
            FROM dws_sentiment_overview
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            LIMIT 1
            """,
            params,
        )
        counts["review_count"] = int((kpi or {}).get("review_count") or 0)
        return {
            "ok": True,
            "data_mode": "warehouse",
            "schema_version": "serving_v2",
            "production_business_metrics": True,
            "export_name": "MySQL serving v2 (Hive DWS sync)",
            "data_scope_summary": self._scope,
            "sentiment_data": (
                f"review_dw DWS sync → {self.settings.mysql_database} (v2)"
            ),
            "aspect_data": "keyword_rules_v1 / fashion_aspects_v1",
            "load_batch_id": self._batch,
            "model_version": self._model,
            "serving_release": "prod_v2",
            "record_counts": counts,
            "source": f"mysql:{self.settings.mysql_database}",
            "mysql_host": self.settings.mysql_host,
            "mysql_user": self.settings.mysql_user,
        }

    def get_kpi(self) -> dict[str, Any]:
        row = self.client.fetch_one(
            """
            SELECT
              review_count,
              product_count,
              positive_count,
              neutral_count,
              negative_count,
              positive_rate,
              neutral_rate,
              negative_rate,
              average_rating,
              average_prediction_score,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_sentiment_overview
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            LIMIT 1
            """,
            self._partition_params(),
        )
        if not row:
            raise ProviderError(
                "dws_sentiment_overview has no row for configured batch/model",
                error="upstream_unavailable",
            )
        row["user_count"] = None
        row["data_scope"] = self._scope
        return row

    def get_top_negative_products(
        self, limit: int, min_reviews: int
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            **self._partition_params(),
            "min_reviews": int(min_reviews),
            "limit": int(limit),
        }
        rows = self.client.fetch_all(
            """
            SELECT
              parent_asin,
              product_title,
              store_name,
              main_category,
              review_count,
              average_rating,
              positive_count,
              neutral_count,
              negative_count,
              positive_rate,
              neutral_rate,
              negative_rate,
              verified_purchase_rate,
              average_helpful_vote,
              average_prediction_score,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_product_sentiment
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
              AND review_count >= %(min_reviews)s
            ORDER BY negative_rate DESC, negative_count DESC, review_count DESC
            LIMIT %(limit)s
            """,
            params,
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_trend(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        recent_days: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {**self._partition_params()}
        clauses = [
            "load_batch_id = %(load_batch_id)s",
            "model_version = %(model_version)s",
        ]
        if start_date:
            clauses.append("dt >= %(start_date)s")
            params["start_date"] = start_date
        if end_date:
            clauses.append("dt <= %(end_date)s")
            params["end_date"] = end_date
        where_sql = " AND ".join(clauses)

        # recent_days: take latest N calendar rows then chronological for charts
        if recent_days is not None and recent_days > 0:
            params["limit"] = int(recent_days)
            rows = self.client.fetch_all(
                f"""
                SELECT
                  dt, review_count, positive_count, neutral_count, negative_count,
                  positive_rate, neutral_rate, negative_rate, average_rating,
                  generated_at, load_batch_id, model_version
                FROM dws_sentiment_daily
                WHERE {where_sql}
                ORDER BY dt DESC
                LIMIT %(limit)s
                """,
                params,
            )
            rows.reverse()
        else:
            limit_sql = ""
            if limit is not None:
                params["limit"] = int(limit)
                limit_sql = " LIMIT %(limit)s"
            rows = self.client.fetch_all(
                f"""
                SELECT
                  dt, review_count, positive_count, neutral_count, negative_count,
                  positive_rate, neutral_rate, negative_rate, average_rating,
                  generated_at, load_batch_id, model_version
                FROM dws_sentiment_daily
                WHERE {where_sql}
                ORDER BY dt ASC
                {limit_sql}
                """,
                params,
            )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_monthly_trend(self) -> list[dict[str, Any]]:
        rows = self.client.fetch_all(
            """
            SELECT
              month_id,
              review_count,
              product_count,
              positive_count,
              neutral_count,
              negative_count,
              positive_rate,
              neutral_rate,
              negative_rate,
              average_rating,
              average_prediction_score,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_monthly_sentiment
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            ORDER BY month_id ASC
            """,
            self._partition_params(),
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_categories(self) -> list[dict[str, Any]]:
        rows = self.client.fetch_all(
            """
            SELECT
              category_key,
              main_category,
              review_count,
              product_count,
              average_rating,
              positive_count,
              neutral_count,
              negative_count,
              positive_rate,
              neutral_rate,
              negative_rate,
              average_prediction_score,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_category_sentiment
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            ORDER BY review_count DESC
            """,
            self._partition_params(),
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_stores(self, limit: int = 10, min_reviews: int = 20) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            **self._partition_params(),
            "limit": int(limit),
            "min_reviews": int(min_reviews),
        }
        rows = self.client.fetch_all(
            """
            SELECT
              store_key,
              store_name,
              review_count,
              product_count,
              average_rating,
              positive_count,
              neutral_count,
              negative_count,
              positive_rate,
              neutral_rate,
              negative_rate,
              average_prediction_score,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_store_sentiment
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
              AND review_count >= %(min_reviews)s
            ORDER BY negative_rate DESC, negative_count DESC, review_count DESC
            LIMIT %(limit)s
            """,
            params,
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_verified_purchase(self) -> list[dict[str, Any]]:
        rows = self.client.fetch_all(
            """
            SELECT
              purchase_status,
              review_count,
              positive_count,
              neutral_count,
              negative_count,
              positive_rate,
              neutral_rate,
              negative_rate,
              average_rating,
              average_helpful_vote,
              average_prediction_score,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_verified_purchase_sentiment
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            ORDER BY review_count DESC
            """,
            self._partition_params(),
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_rating_matrix(self) -> list[dict[str, Any]]:
        rows = self.client.fetch_all(
            """
            SELECT
              rating_value,
              pred_label,
              review_count,
              rate_within_rating,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_rating_prediction_matrix
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            ORDER BY rating_value ASC, pred_label ASC
            """,
            self._partition_params(),
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_confidence(self) -> list[dict[str, Any]]:
        rows = self.client.fetch_all(
            """
            SELECT
              bucket_code,
              bucket_order,
              minimum_score,
              maximum_score,
              review_count,
              positive_count,
              neutral_count,
              negative_count,
              average_prediction_score,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_prediction_confidence
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            ORDER BY bucket_order ASC
            """,
            self._partition_params(),
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_aspects(self, aspect: str | None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {**self._partition_params()}
        clauses = [
            "load_batch_id = %(load_batch_id)s",
            "model_version = %(model_version)s",
        ]
        if aspect:
            clauses.append(
                "(LOWER(aspect_code) = %(aspect)s OR LOWER(aspect_name) = %(aspect)s)"
            )
            params["aspect"] = aspect.strip().lower()
        where_sql = " AND ".join(clauses)
        rows = self.client.fetch_all(
            f"""
            SELECT
              aspect_code,
              aspect_name,
              mention_count,
              product_count,
              positive_count,
              neutral_count,
              negative_count,
              positive_rate,
              neutral_rate,
              negative_rate,
              average_prediction_score,
              extraction_method,
              rule_version,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_aspect_summary
            WHERE {where_sql}
            ORDER BY mention_count DESC, negative_rate DESC
            """,
            params,
        )
        mapped: list[dict[str, Any]] = []
        for row in rows:
            mapped.append(
                {
                    # Contract-compatible aliases for smoke dashboard
                    "aspect": row.get("aspect_code"),
                    "reason_code": row.get("aspect_code"),
                    "reason_name": row.get("aspect_name"),
                    "mention_count": row.get("mention_count"),
                    "product_count": row.get("product_count"),
                    "positive_count": row.get("positive_count"),
                    "neutral_count": row.get("neutral_count"),
                    "negative_count": row.get("negative_count"),
                    "positive_rate": row.get("positive_rate"),
                    "neutral_rate": row.get("neutral_rate"),
                    "negative_rate": row.get("negative_rate"),
                    "average_confidence": row.get("average_prediction_score"),
                    "average_prediction_score": row.get("average_prediction_score"),
                    "extractor_version": row.get("rule_version"),
                    "extraction_method": row.get("extraction_method"),
                    "rule_version": row.get("rule_version"),
                    "generated_at": row.get("generated_at"),
                    "load_batch_id": row.get("load_batch_id"),
                    "model_version": row.get("model_version"),
                    "data_scope": self._scope,
                }
            )
        return mapped

    def get_negative_reasons(
        self, limit: int, parent_asin: str | None
    ) -> list[dict[str, Any]]:
        # v2 grain is global reason_code (not per-product). parent_asin filter → empty.
        if parent_asin and parent_asin.strip():
            return []
        params: dict[str, Any] = {
            **self._partition_params(),
            "limit": int(limit),
        }
        rows = self.client.fetch_all(
            """
            SELECT
              reason_code,
              reason_name,
              mention_count,
              product_count,
              share_of_negative_reviews,
              average_prediction_score,
              extraction_method,
              rule_version,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_negative_reasons
            WHERE load_batch_id = %(load_batch_id)s
              AND model_version = %(model_version)s
            ORDER BY mention_count DESC, share_of_negative_reviews DESC
            LIMIT %(limit)s
            """,
            params,
        )
        mapped: list[dict[str, Any]] = []
        for row in rows:
            mapped.append(
                {
                    "parent_asin": "",
                    "product_title": "",
                    "aspect": "",
                    "reason_code": row.get("reason_code"),
                    "reason_name": row.get("reason_name"),
                    "reason_count": row.get("mention_count"),
                    "reason_share": row.get("share_of_negative_reviews"),
                    "mention_count": row.get("mention_count"),
                    "product_count": row.get("product_count"),
                    "share_of_negative_reviews": row.get("share_of_negative_reviews"),
                    "average_prediction_score": row.get("average_prediction_score"),
                    "extractor_version": row.get("rule_version"),
                    "extraction_method": row.get("extraction_method"),
                    "rule_version": row.get("rule_version"),
                    "generated_at": row.get("generated_at"),
                    "load_batch_id": row.get("load_batch_id"),
                    "model_version": row.get("model_version"),
                    "data_scope": self._scope,
                }
            )
        return mapped

    def get_alerts(
        self,
        *,
        limit: int = 20,
        alert_level: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            **self._partition_params(),
            "limit": int(limit),
        }
        clauses = [
            "load_batch_id = %(load_batch_id)s",
            "model_version = %(model_version)s",
        ]
        if alert_level:
            clauses.append("LOWER(alert_level) = %(alert_level)s")
            params["alert_level"] = alert_level.strip().lower()
        where_sql = " AND ".join(clauses)
        rows = self.client.fetch_all(
            f"""
            SELECT
              alert_id,
              alert_type,
              alert_level,
              entity_type,
              entity_id,
              entity_name,
              metric_name,
              metric_value,
              threshold_value,
              review_count,
              alert_message,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_sentiment_alerts
            WHERE {where_sql}
            ORDER BY
              CASE LOWER(alert_level)
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 9
              END,
              metric_value DESC
            LIMIT %(limit)s
            """,
            params,
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows

    def get_samples(
        self,
        *,
        limit: int = 20,
        pred_label: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            **self._partition_params(),
            "limit": int(limit),
        }
        clauses = [
            "load_batch_id = %(load_batch_id)s",
            "model_version = %(model_version)s",
        ]
        if pred_label:
            clauses.append("LOWER(pred_label) = %(pred_label)s")
            params["pred_label"] = pred_label.strip().lower()
        where_sql = " AND ".join(clauses)
        rows = self.client.fetch_all(
            f"""
            SELECT
              sample_id,
              parent_asin,
              product_title,
              main_category,
              rating,
              pred_label,
              pred_score,
              review_text_preview,
              text_length,
              review_time,
              sample_rank,
              generated_at,
              load_batch_id,
              model_version
            FROM dws_review_samples
            WHERE {where_sql}
            ORDER BY sample_rank ASC, pred_score DESC
            LIMIT %(limit)s
            """,
            params,
        )
        for row in rows:
            row["data_scope"] = self._scope
        return rows
