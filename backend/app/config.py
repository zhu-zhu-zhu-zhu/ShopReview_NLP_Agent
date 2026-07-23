from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> repo root is parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]

# Load repo-root .env then backend/.env (later does not override existing)
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "backend" / ".env")


def _split_origins(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


class Settings:
    def __init__(self) -> None:
        # Production build: MySQL warehouse is the only supported data source.
        self.data_mode: str = "warehouse"
        self.api_host: str = os.getenv("API_HOST", "127.0.0.1").strip()
        self.api_port: int = int(os.getenv("API_PORT", "8080"))
        self.cors_origins: list[str] = _split_origins(
            os.getenv(
                "CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            )
        )

        # Scheme C: MySQL serving layer (read-only)
        self.mysql_host: str = os.getenv("MYSQL_HOST", "").strip()
        self.mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
        self.mysql_user: str = os.getenv("MYSQL_USER", "agent_reader").strip()
        self.mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
        self.mysql_database: str = os.getenv(
            "MYSQL_DATABASE", "shopreview_serving"
        ).strip()
        self.mysql_connect_timeout: int = int(
            os.getenv("MYSQL_CONNECT_TIMEOUT", "8")
        )
        self.mysql_read_timeout: int = int(os.getenv("MYSQL_READ_TIMEOUT", "60"))

        self.warehouse_load_batch_id: str = os.getenv(
            "WAREHOUSE_LOAD_BATCH_ID", "prod_v1_100k"
        ).strip()
        self.warehouse_model_version: str = os.getenv(
            "WAREHOUSE_MODEL_VERSION", "tfidf_logreg_oof_v1"
        ).strip()
        self.warehouse_data_scope: str = os.getenv(
            "WAREHOUSE_DATA_SCOPE",
            f"{self.warehouse_load_batch_id}+{self.warehouse_model_version}",
        ).strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
