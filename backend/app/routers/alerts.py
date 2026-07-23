from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.providers import get_provider
from app.providers.base import ProviderError

router = APIRouter(tags=["alerts"])


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


@router.get("/api/alerts", response_model=None)
def alerts(
    limit: int = Query(default=20, ge=1, le=200),
    alert_level: str | None = Query(default=None),
) -> Any:
    try:
        provider = get_provider()
        rows = provider.get_alerts(
            limit=_clamp(limit, 1, 200),
            alert_level=alert_level,
        )
        meta = provider.response_meta("warehouse:dws_sentiment_alerts")
        return {"ok": True, "data": rows, "meta": meta}
    except ProviderError as exc:
        status = 501 if exc.error == "not_available" else 500
        return JSONResponse(
            status_code=status,
            content={
                "ok": False,
                "error": exc.error,
                "message": exc.message,
                "meta": {
                    "data_mode": get_settings().data_mode,
                    "schema_version": "draft_v0.1",
                    "production_business_metrics": True,
                },
            },
        )
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={
                "ok": False,
                "error": "not_implemented",
                "message": str(exc),
            },
        )
