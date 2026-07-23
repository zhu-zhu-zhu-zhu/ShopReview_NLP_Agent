"""Serving-v2 aggregate endpoints: category / store / verified / matrix / confidence."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.providers import get_provider
from app.providers.base import ProviderError
from app.providers.warehouse import WarehouseProvider

router = APIRouter(tags=["serving-v2"])


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


def _meta(provider: Any, source: str) -> dict[str, Any]:
    if isinstance(provider, WarehouseProvider):
        return provider.response_meta(source)
    return provider.response_meta(source)


@router.get("/api/categories", response_model=None)
def categories() -> Any:
    try:
        provider = get_provider()
        rows = provider.get_categories()
        return {
            "ok": True,
            "data": rows,
            "meta": _meta(provider, "warehouse:dws_category_sentiment"),
        }
    except ProviderError as exc:
        return _err(exc)
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "not_implemented", "message": str(exc)},
        )


@router.get("/api/stores", response_model=None)
def stores(
    limit: int = Query(default=10, ge=1, le=50),
    min_reviews: int = Query(default=20, ge=0),
) -> Any:
    try:
        provider = get_provider()
        rows = provider.get_stores(
            limit=_clamp(limit, 1, 50),
            min_reviews=min_reviews,
        )
        return {
            "ok": True,
            "data": rows,
            "meta": _meta(provider, "warehouse:dws_store_sentiment"),
        }
    except ProviderError as exc:
        return _err(exc)
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "not_implemented", "message": str(exc)},
        )


@router.get("/api/verified-purchase", response_model=None)
def verified_purchase() -> Any:
    try:
        provider = get_provider()
        rows = provider.get_verified_purchase()
        return {
            "ok": True,
            "data": rows,
            "meta": _meta(provider, "warehouse:dws_verified_purchase_sentiment"),
        }
    except ProviderError as exc:
        return _err(exc)
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "not_implemented", "message": str(exc)},
        )


@router.get("/api/rating-matrix", response_model=None)
def rating_matrix() -> Any:
    try:
        provider = get_provider()
        rows = provider.get_rating_matrix()
        return {
            "ok": True,
            "data": rows,
            "meta": _meta(provider, "warehouse:dws_rating_prediction_matrix"),
        }
    except ProviderError as exc:
        return _err(exc)
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "not_implemented", "message": str(exc)},
        )


@router.get("/api/confidence", response_model=None)
def confidence() -> Any:
    try:
        provider = get_provider()
        rows = provider.get_confidence()
        return {
            "ok": True,
            "data": rows,
            "meta": _meta(provider, "warehouse:dws_prediction_confidence"),
        }
    except ProviderError as exc:
        return _err(exc)
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "not_implemented", "message": str(exc)},
        )
