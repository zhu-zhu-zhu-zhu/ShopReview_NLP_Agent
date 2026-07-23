from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.providers import get_provider
from app.providers.base import ProviderError
from app.providers.smoke_json import SmokeJsonProvider
from app.providers.warehouse import WarehouseProvider

router = APIRouter(tags=["negative-reasons"])


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _provider_error_response(exc: ProviderError) -> JSONResponse:
    status = (
        501 if exc.error in {"not_available", "not_available_in_smoke"} else 500
    )
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": exc.error, "message": exc.message},
    )


@router.get("/api/negative-reasons", response_model=None)
def negative_reasons(
    limit: int = Query(default=20),
    parent_asin: str | None = Query(default=None),
) -> Any:
    limit = _clamp(limit, 1, 100)
    try:
        provider = get_provider()
        rows = provider.get_negative_reasons(
            limit=limit, parent_asin=parent_asin
        )
        if isinstance(provider, SmokeJsonProvider):
            meta = provider.dataset_meta("negative_reasons.json")
        elif isinstance(provider, WarehouseProvider):
            meta = provider.response_meta("warehouse:negative-reasons")
        else:
            meta = provider.response_meta("warehouse:negative-reasons")
        return {"ok": True, "data": rows, "meta": meta}
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
