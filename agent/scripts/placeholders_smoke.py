"""H6 self-check: placeholder tools via HttpApiAdapter (Scheme A).

    set PYTHONPATH=%CD%
    .venv\\Scripts\\python.exe -m agent.scripts.placeholders_smoke
"""

from __future__ import annotations

import sys

from agent.tools import openai_tools, run_tool


EXPECT = {
    "get_sentiment_trend": "GET /api/trend",
    "get_alerts": "GET /api/alerts",
    "search_review_samples": "GET /api/samples",
}


def main() -> int:
    names = {t["function"]["name"] for t in openai_tools()}
    for name in EXPECT:
        if name not in names:
            print(f"FAIL: {name} missing from openai_tools()")
            return 1

    for name, source in EXPECT.items():
        result = run_tool(name, {})
        print(
            name,
            "ok=",
            result.get("ok"),
            "error=",
            result.get("error"),
            "source=",
            result.get("source"),
        )
        if result.get("ok"):
            print(f"FAIL: {name} should be ok=false")
            return 2
        if result.get("error") != "not_available_in_smoke":
            print(f"FAIL: {name} expected not_available_in_smoke, got {result.get('error')}")
            return 3
        if result.get("source") != source:
            print(f"FAIL: {name} expected source={source}, got {result.get('source')}")
            return 4

    print("PLACEHOLDERS_SMOKE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
