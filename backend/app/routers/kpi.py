from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.providers import get_provider
from app.providers.base import ProviderError
from app.providers.smoke_json import SmokeJsonProvider
from app.providers.warehouse import WarehouseProvider

router = APIRouter(tags=["kpi"])


def _wrap(data: Any, meta: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data, "meta": meta}


def _provider_error_response(exc: ProviderError) -> JSONResponse:
    status = (
        501 if exc.error in {"not_available", "not_available_in_smoke"} else 500
    )
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": exc.error, "message": exc.message},
    )


@router.get("/api/kpi", response_model=None)
def kpi(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
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
        row = provider.get_kpi()
        if isinstance(provider, SmokeJsonProvider):
            meta = provider.dataset_meta("sentiment_overview.json")
        elif isinstance(provider, WarehouseProvider):
            meta = provider.response_meta(
                "warehouse:dws_sentiment_overview",
                data_scope=str(row.get("data_scope") or ""),
            )
        else:
            meta = provider.response_meta("warehouse:kpi")
        if start_date and end_date:
            meta = {
                **meta,
                "message": "当前为快照数据，不支持时间窗过滤；已忽略 start_date/end_date",
            }
        return _wrap(row, meta)
    except ProviderError as exc:
        return _provider_error_response(exc)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "ok": False,
                "error": "not_implemented",
                "message": str(exc),
            },
        ) from exc
