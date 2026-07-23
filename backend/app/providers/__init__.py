from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.providers.base import MetricsProvider, ProviderError
from app.providers.smoke_json import SmokeJsonProvider
from app.providers.warehouse import WarehouseProvider


@lru_cache
def get_provider() -> MetricsProvider:
    settings = get_settings()
    if settings.data_mode == "smoke":
        return SmokeJsonProvider(
            export_dir=settings.smoke_export_dir,
            data_mode=settings.data_mode,
        )
    if settings.data_mode == "warehouse":
        return WarehouseProvider(settings)
    raise ProviderError(
        f"Unsupported DATA_MODE={settings.data_mode!r}; use smoke|warehouse",
        error="invalid_args",
    )


def reset_provider_cache() -> None:
    get_provider.cache_clear()
    get_settings.cache_clear()
