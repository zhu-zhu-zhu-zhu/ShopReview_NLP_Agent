from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.providers import get_provider
from app.providers.base import ProviderError
from app.providers.warehouse import WarehouseProvider

router = APIRouter(tags=["trend"])


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _err(exc: ProviderError) -> JSONResponse:
    status = (
        501 if exc.error in {"not_available", "not_available_in_smoke"} else 500
    )
    return JSONResponse(
        status_code=status,
        content={
            "ok": False,
            "error": exc.error,
            "message": exc.message,
            "meta": {
                "data_mode": get_settings().data_mode,
                "schema_version": "serving_v2",
                "production_business_metrics": get_settings().data_mode
                == "warehouse",
            },
        },
    )


@router.get("/api/trend", response_model=None)
def trend(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=5000),
    recent_days: int | None = Query(default=None, ge=1, le=5000),
) -> Any:
    if (start_date and not end_date) or (end_date and not start_date):
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": "invalid_args",
                "message": "Provide both start_date and end_date, or neither",
            },
        )
    try:
        provider = get_provider()
        capped = _clamp(limit, 1, 5000) if limit is not None else None
        recent = _clamp(recent_days, 1, 5000) if recent_days is not None else None
        rows = provider.get_trend(
            start_date=start_date,
            end_date=end_date,
            limit=capped,
            recent_days=recent,
        )
        if isinstance(provider, WarehouseProvider):
            meta = provider.response_meta("warehouse:dws_sentiment_daily")
        else:
            meta = provider.response_meta("smoke:trend")
        return {"ok": True, "data": rows, "meta": meta}
    except ProviderError as exc:
        return _err(exc)
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "not_implemented", "message": str(exc)},
        )


@router.get("/api/trends/monthly", response_model=None)
def monthly_trend() -> Any:
    try:
        provider = get_provider()
        rows = provider.get_monthly_trend()
        if isinstance(provider, WarehouseProvider):
            meta = provider.response_meta("warehouse:dws_monthly_sentiment")
        else:
            meta = provider.response_meta("smoke:monthly")
        return {"ok": True, "data": rows, "meta": meta}
    except ProviderError as exc:
        return _err(exc)
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "not_implemented", "message": str(exc)},
        )
