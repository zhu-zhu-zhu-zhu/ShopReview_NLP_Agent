from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.providers.base import MetricsProvider
from app.providers.warehouse import WarehouseProvider


@lru_cache
def get_provider() -> MetricsProvider:
    return WarehouseProvider(get_settings())


def reset_provider_cache() -> None:
    get_provider.cache_clear()
    get_settings.cache_clear()
