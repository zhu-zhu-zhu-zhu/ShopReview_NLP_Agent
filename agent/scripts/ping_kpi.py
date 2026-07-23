"""H0 self-check: HttpApiAdapter can read Stage G /api/kpi.

Run from repo root:

    set PYTHONPATH=%CD%
    .venv\\Scripts\\python.exe -m agent.scripts.ping_kpi
"""

from __future__ import annotations

import sys

from agent.adapters.http_api import HttpApiAdapter
from agent.config import get_settings


GOLDEN = {
    "review_count": 50,
    "positive_count": 44,
    "neutral_count": 6,
    "negative_count": 0,
    "positive_rate": 0.88,
    "neutral_rate": 0.12,
    "negative_rate": 0.0,
    "average_rating": 4.46,
}


def main() -> int:
    settings = get_settings()
    print(f"BACKEND_BASE_URL={settings.backend_base_url}")
    print(f"AGENT_DATA_MODE={settings.data_mode}")

    adapter = HttpApiAdapter(settings)
    result = adapter.get_kpi()
    if not result.get("ok"):
        print("PING_KPI_FAIL", result.get("error"), result.get("message"))
        return 1

    data = result.get("data") or {}
    mismatches = []
    for key, expected in GOLDEN.items():
        actual = data.get(key)
        if actual != expected:
            # float tolerance for rates / rating
            if isinstance(expected, float) and isinstance(actual, (int, float)):
                if abs(float(actual) - expected) < 1e-9:
                    continue
            mismatches.append((key, expected, actual))

    if mismatches:
        print("PING_KPI_MISMATCH")
        for key, expected, actual in mismatches:
            print(f"  {key}: expected={expected!r} actual={actual!r}")
        return 2

    print(
        "PING_KPI_OK",
        f"review_count={data.get('review_count')}",
        f"negative_rate={data.get('negative_rate')}",
        f"data_scope={result.get('data_scope')}",
        f"source={result.get('source')}",
    )

    # Extra smoke: placeholders should fail honestly
    trend = adapter.get_trend()
    if trend.get("ok"):
        print("PING_TREND_UNEXPECTED_OK")
        return 3
    print(
        "PING_TREND_OK",
        f"error={trend.get('error')}",
        f"source={trend.get('source')}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
