from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.providers import get_provider
from app.providers.base import ProviderError

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict[str, Any]:
    try:
        return get_provider().get_health_meta()
    except ProviderError as exc:
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "error": exc.error, "message": exc.message},
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "ok": False,
                "error": "not_implemented",
                "message": str(exc),
            },
        ) from exc
