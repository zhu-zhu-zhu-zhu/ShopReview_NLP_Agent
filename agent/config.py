"""Agent settings loaded from environment / .env files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def repo_root() -> Path:
    """Repository root (parent of the ``agent/`` package)."""
    return Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = repo_root()
    # Prefer agent/.env, then repo root .env
    for path in (root / "agent" / ".env", root / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_float(name: str, default: float) -> float:
    raw = _env(name, "")
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = _env(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    data_mode: str
    backend_base_url: str
    http_timeout_sec: float
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_timeout_sec: float
    max_steps: int
    temperature: float

    @property
    def repo_root(self) -> Path:
        return repo_root()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()
    base = _env("BACKEND_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    return Settings(
        data_mode="warehouse",
        backend_base_url=base,
        http_timeout_sec=_env_float("HTTP_TIMEOUT_SEC", 15.0),
        llm_api_key=_env("LLM_API_KEY", ""),
        llm_base_url=_env("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        llm_model=_env("LLM_MODEL", "deepseek-v4-flash"),
        llm_timeout_sec=_env_float("LLM_TIMEOUT_SEC", 60.0),
        max_steps=_env_int("AGENT_MAX_STEPS", 6),
        temperature=_env_float("AGENT_TEMPERATURE", 0.2),
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()
