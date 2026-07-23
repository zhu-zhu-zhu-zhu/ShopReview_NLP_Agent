from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.providers import get_provider
from app.providers.base import ProviderError
from app.providers.warehouse import WarehouseProvider

router = APIRouter(tags=["samples"])


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


@router.get("/api/samples", response_model=None)
def samples(
    limit: int = Query(default=20, ge=1, le=150),
    pred_label: str | None = Query(default=None),
) -> Any:
    try:
        provider = get_provider()
        rows = provider.get_samples(
            limit=_clamp(limit, 1, 150),
            pred_label=pred_label,
        )
        if isinstance(provider, WarehouseProvider):
            meta = provider.response_meta("warehouse:dws_review_samples")
            meta["message"] = "脱敏预览字段 review_text_preview；不含 user_id / 全文"
        else:
            meta = provider.response_meta("smoke:samples")
        return {"ok": True, "data": rows, "meta": meta}
    except ProviderError as exc:
        status = (
            501
            if exc.error in {"not_available", "not_available_in_smoke"}
            else 500
        )
        return JSONResponse(
            status_code=status,
            content={
                "ok": False,
                "error": exc.error,
                "message": exc.message,
                "meta": {
                    "data_mode": get_settings().data_mode,
                    "schema_version": "draft_v0.1",
                    "production_business_metrics": get_settings().data_mode
                    == "warehouse",
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
