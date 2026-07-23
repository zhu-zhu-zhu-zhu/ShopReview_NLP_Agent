"""HTTP adapter — Stage G FastAPI metrics (primary path)."""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from agent.adapters.base import (
    AdapterResult,
    MetricsAdapter,
    fail_result,
    ok_result,
)
from agent.config import Settings, get_settings


class HttpApiAdapter(MetricsAdapter):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.backend_base_url.rstrip("/")
        self.timeout = self.settings.http_timeout_sec

    def _get(self, path: str, params: dict[str, Any] | None = None) -> AdapterResult:
        query = ""
        if params:
            cleaned = {
                k: v for k, v in params.items() if v is not None and v != ""
            }
            if cleaned:
                query = "?" + urlencode(cleaned)
        url = f"{self.base_url}{path}{query}"
        source = f"GET {path}"
        req = Request(url, method="GET", headers={"Accept": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                status = getattr(resp, "status", 200)
                body_raw = resp.read().decode("utf-8")
                return self._parse_body(body_raw, status=status, source=source, path=path)
        except HTTPError as exc:
            body_raw = ""
            try:
                body_raw = exc.read().decode("utf-8")
            except Exception:
                pass
            return self._parse_body(
                body_raw,
                status=exc.code,
                source=source,
                path=path,
                fallback_error=f"http_{exc.code}",
            )
        except URLError as exc:
            return fail_result(
                "upstream_unavailable",
                source=source,
                message=(
                    f"无法连接后端 {self.base_url}（{exc.reason}）。"
                    "请先启动 backend\\start.bat"
                ),
            )
        except TimeoutError:
            return fail_result(
                "timeout",
                source=source,
                message=f"请求超时（{self.timeout}s）：{url}",
            )
        except Exception as exc:  # noqa: BLE001 — surface as tool failure
            return fail_result(
                "upstream_unavailable",
                source=source,
                message=str(exc),
            )

    def _parse_body(
        self,
        body_raw: str,
        *,
        status: int,
        source: str,
        path: str,
        fallback_error: str | None = None,
    ) -> AdapterResult:
        try:
            payload = json.loads(body_raw) if body_raw else {}
        except json.JSONDecodeError:
            return fail_result(
                fallback_error or f"http_{status}",
                source=source,
                message=f"非 JSON 响应 HTTP {status}: {body_raw[:200]}",
            )

        if not isinstance(payload, dict):
            return fail_result(
                "invalid_response",
                source=source,
                message="响应根节点不是 object",
            )

        # health: flat fields at root (no data wrapper required)
        if path == "/api/health":
            if payload.get("ok") is True or status == 200:
                meta_bits = {
                    "data_scope": str(
                        payload.get("data_scope_summary")
                        or payload.get("data_scope")
                        or ""
                    ),
                    "schema_version": str(payload.get("schema_version") or "draft_v0.1"),
                    "production_business_metrics": bool(
                        payload.get("production_business_metrics", False)
                    ),
                }
                return ok_result(
                    payload,
                    source=source,
                    data_scope=meta_bits["data_scope"],
                    schema_version=meta_bits["schema_version"],
                    production_business_metrics=meta_bits[
                        "production_business_metrics"
                    ],
                )
            return fail_result(
                str(payload.get("error") or fallback_error or f"http_{status}"),
                source=source,
                message=str(payload.get("message") or body_raw[:200]),
            )

        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        data_scope = str(meta.get("data_scope") or "")
        schema_version = str(meta.get("schema_version") or "draft_v0.1")
        prod = bool(meta.get("production_business_metrics", False))
        meta_message = meta.get("message")

        if status == 200 and payload.get("ok") is True:
            return ok_result(
                payload.get("data"),
                source=source,
                data_scope=data_scope,
                schema_version=schema_version,
                production_business_metrics=prod,
                message=str(meta_message) if meta_message else None,
            )

        err = payload.get("error") or fallback_error or f"http_{status}"
        msg = payload.get("message") or payload.get("detail")
        if isinstance(msg, dict):
            err = msg.get("error") or err
            msg = msg.get("message") or str(msg)
        return fail_result(
            str(err),
            source=source,
            message=str(msg) if msg else f"HTTP {status}",
            data_scope=data_scope,
            schema_version=schema_version,
            production_business_metrics=prod,
        )

    def get_health(self) -> AdapterResult:
        return self._get("/api/health")

    def get_kpi(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AdapterResult:
        return self._get(
            "/api/kpi",
            {"start_date": start_date, "end_date": end_date},
        )

    def get_top_negative_products(
        self,
        limit: int = 5,
        min_reviews: int = 1,
    ) -> AdapterResult:
        return self._get(
            "/api/top-negative-products",
            {"limit": limit, "min_reviews": min_reviews},
        )

    def get_aspects(self, aspect: str | None = None) -> AdapterResult:
        return self._get("/api/aspects", {"aspect": aspect})

    def get_negative_reasons(
        self,
        limit: int = 10,
        parent_asin: str | None = None,
    ) -> AdapterResult:
        return self._get(
            "/api/negative-reasons",
            {"limit": limit, "parent_asin": parent_asin},
        )

    def get_trend(self) -> AdapterResult:
        return self._get("/api/trend")

    def get_alerts(self) -> AdapterResult:
        return self._get("/api/alerts")

    def get_samples(self) -> AdapterResult:
        return self._get("/api/samples")
