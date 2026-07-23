from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator, Mapping, Sequence

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from app.config import Settings
from app.providers.base import ProviderError


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _jsonable(val) for key, val in row.items()}


class MysqlReadClient:
    """Read-only MySQL access via parameterized SELECT only."""

    def __init__(self, settings: Settings) -> None:
        if not settings.mysql_host:
            raise ProviderError(
                "MYSQL_HOST is required when DATA_MODE=warehouse",
                error="upstream_unavailable",
            )
        if not settings.mysql_password:
            raise ProviderError(
                "MYSQL_PASSWORD is required when DATA_MODE=warehouse",
                error="upstream_unavailable",
            )
        self._settings = settings

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        conn: Connection | None = None
        try:
            conn = pymysql.connect(
                host=self._settings.mysql_host,
                port=self._settings.mysql_port,
                user=self._settings.mysql_user,
                password=self._settings.mysql_password,
                database=self._settings.mysql_database,
                charset="utf8mb4",
                cursorclass=DictCursor,
                connect_timeout=self._settings.mysql_connect_timeout,
                read_timeout=self._settings.mysql_read_timeout,
                write_timeout=self._settings.mysql_read_timeout,
                autocommit=True,
            )
            yield conn
        except pymysql.Error as exc:
            raise ProviderError(
                f"MySQL connection/query failed: {exc}",
                error="upstream_unavailable",
            ) from exc
        finally:
            if conn is not None:
                conn.close()

    def fetch_all(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall() or []
                return [normalize_row(row) for row in rows]

    def fetch_one(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def fetch_value(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> Any:
        row = self.fetch_one(sql, params)
        if not row:
            return None
        return next(iter(row.values()))
