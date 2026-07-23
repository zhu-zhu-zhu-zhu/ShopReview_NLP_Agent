"""Production self-check for the KPI and trend warehouse APIs.

Run from repo root:

    set PYTHONPATH=%CD%
    .venv\\Scripts\\python.exe -m agent.scripts.ping_kpi
"""

from __future__ import annotations

import sys

from agent.adapters.http_api import HttpApiAdapter
from agent.config import get_settings


EXPECTED_REVIEW_COUNT = 99_703


def main() -> int:
    settings = get_settings()
    print(f"BACKEND_BASE_URL={settings.backend_base_url}")
    print(f"DATA_MODE={settings.data_mode}")

    adapter = HttpApiAdapter(settings)
    result = adapter.get_kpi()
    if not result.get("ok"):
        print("PING_KPI_FAIL", result.get("error"), result.get("message"))
        return 1

    data = result.get("data") or {}
    if data.get("review_count") != EXPECTED_REVIEW_COUNT:
        print(
            "PING_KPI_MISMATCH",
            f"expected_review_count={EXPECTED_REVIEW_COUNT}",
            f"actual_review_count={data.get('review_count')}",
        )
        return 2

    print(
        "PING_KPI_OK",
        f"review_count={data.get('review_count')}",
        f"negative_rate={data.get('negative_rate')}",
        f"data_scope={result.get('data_scope')}",
        f"source={result.get('source')}",
    )

    trend = adapter.get_trend()
    if not trend.get("ok"):
        print("PING_TREND_FAIL", trend.get("error"), trend.get("message"))
        return 3
    print(
        "PING_TREND_OK",
        f"rows={len(trend.get('data') or [])}",
        f"source={trend.get('source')}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
