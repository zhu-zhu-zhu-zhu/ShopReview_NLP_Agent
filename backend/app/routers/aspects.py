from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.providers import get_provider
from app.providers.base import ProviderError

router = APIRouter(tags=["aspects"])


def _provider_error_response(exc: ProviderError) -> JSONResponse:
    status = 501 if exc.error == "not_available" else 500
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": exc.error, "message": exc.message},
    )


@router.get("/api/aspects", response_model=None)
def aspects(aspect: str | None = Query(default=None)) -> Any:
    try:
        provider = get_provider()
        rows = provider.get_aspects(aspect=aspect)
        meta = provider.response_meta("warehouse:aspects")
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
