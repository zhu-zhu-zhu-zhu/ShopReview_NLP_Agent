from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.providers import get_provider
from app.providers.base import ProviderError
from app.providers.smoke_json import SmokeJsonProvider
from app.providers.warehouse import WarehouseProvider

router = APIRouter(tags=["products"])


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


@router.get("/api/top-negative-products", response_model=None)
def top_negative_products(
    limit: int = Query(default=10),
    min_reviews: int = Query(default=1),
) -> Any:
    limit = _clamp(limit, 1, 50)
    if min_reviews < 0:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": "invalid_args",
                "message": "min_reviews must be >= 0",
            },
        )
    try:
        provider = get_provider()
        rows = provider.get_top_negative_products(
            limit=limit, min_reviews=min_reviews
        )
        if isinstance(provider, SmokeJsonProvider):
            meta = provider.dataset_meta("product_sentiment.json")
        elif isinstance(provider, WarehouseProvider):
            meta = provider.response_meta("warehouse:dws_product_sentiment")
        else:
            meta = provider.response_meta("warehouse:top-negative-products")
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
