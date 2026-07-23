from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.providers import get_provider, reset_provider_cache
from app.providers.base import ProviderError
from app.routers import (
    agent_chat,
    alerts,
    aspects,
    health,
    kpi,
    negative_reasons,
    products,
    samples,
    serving_v2,
    trend,
)

logger = logging.getLogger("shopreview.backend")

app = FastAPI(
    title="ShopReview Metrics API",
    version="0.4.0",
    description="Production MySQL warehouse metrics service for dashboard and Agent",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(kpi.router)
app.include_router(products.router)
app.include_router(aspects.router)
app.include_router(negative_reasons.router)
app.include_router(trend.router)
app.include_router(alerts.router)
app.include_router(samples.router)
app.include_router(serving_v2.router)
app.include_router(agent_chat.router)


@app.on_event("startup")
def validate_provider_on_startup() -> None:
    reset_provider_cache()
    cfg = get_settings()
    logger.info(
        "Starting production API data_mode=%s mysql_host=%s",
        cfg.data_mode,
        cfg.mysql_host or "-",
    )
    try:
        provider = get_provider()
        meta = provider.get_health_meta()
        logger.info(
            "Warehouse provider OK model=%s batch=%s counts=%s",
            meta.get("model_version"),
            meta.get("load_batch_id"),
            meta.get("record_counts"),
        )
    except ProviderError as exc:
        logger.error(
            "Warehouse MySQL not reachable at startup: %s "
            "(API will return 500/upstream_unavailable until network is up)",
            exc.message,
        )
