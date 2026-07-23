"""H1 self-check: four tools + schemas + invalid cases.

Run from repo root (Stage G API must be up):

    set PYTHONPATH=%CD%
    .venv\\Scripts\\python.exe -m agent.scripts.tools_smoke
"""

from __future__ import annotations

import sys

from agent.tools import openai_tools, run_tool, tool_names
from agent.tools.base import summarize_for_step

GOLDEN_KPI = {
    "review_count": 50,
    "positive_count": 44,
    "neutral_count": 6,
    "negative_count": 0,
    "positive_rate": 0.88,
    "neutral_rate": 0.12,
    "negative_rate": 0.0,
    "average_rating": 4.46,
}


def _close(a: object, b: object) -> bool:
    if isinstance(b, float) and isinstance(a, (int, float)):
        return abs(float(a) - b) < 1e-9
    return a == b


def main() -> int:
    print("tools:", ", ".join(tool_names()))
    schemas = openai_tools()
    print(f"openai_tools_count={len(schemas)}")
    if len(schemas) < 4:
        print("FAIL: openai_tools() must return >= 4")
        return 1

    # --- get_kpi ---
    kpi = run_tool("get_kpi", {})
    print("get_kpi", kpi.get("ok"), summarize_for_step("get_kpi", kpi))
    if not kpi.get("ok"):
        print("FAIL get_kpi", kpi.get("error"), kpi.get("message"))
        return 2
    data = kpi.get("data") or {}
    for key, expected in GOLDEN_KPI.items():
        if not _close(data.get(key), expected):
            print(f"FAIL kpi {key}: expected={expected!r} actual={data.get(key)!r}")
            return 3

    # dates forwarded (must not fail on smoke)
    kpi_dates = run_tool(
        "get_kpi",
        {"start_date": "2026-01-01", "end_date": "2026-01-07"},
    )
    if not kpi_dates.get("ok"):
        print("FAIL get_kpi with dates", kpi_dates)
        return 4
    print("get_kpi+dates", "ok", summarize_for_step("get_kpi", kpi_dates))

    # --- top negative ---
    products = run_tool(
        "get_top_negative_products",
        {"limit": 5, "min_reviews": 1},
    )
    print(
        "get_top_negative_products",
        products.get("ok"),
        summarize_for_step("get_top_negative_products", products),
    )
    if not products.get("ok"):
        print("FAIL products", products)
        return 5
    rows = products.get("data") or []
    if not isinstance(rows, list) or len(rows) < 1:
        print("FAIL products empty")
        return 6
    if "parent_asin" not in rows[0]:
        print("FAIL missing parent_asin", rows[0])
        return 7

    # --- aspects ---
    aspects = run_tool("get_aspect_stats", {})
    print(
        "get_aspect_stats",
        aspects.get("ok"),
        summarize_for_step("get_aspect_stats", aspects),
    )
    if not aspects.get("ok") or not (aspects.get("data") or []):
        print("FAIL aspects", aspects)
        return 8

    aspects_size = run_tool("get_aspect_stats", {"aspect": "size"})
    print(
        "get_aspect_stats(size)",
        aspects_size.get("ok"),
        summarize_for_step("get_aspect_stats", aspects_size),
    )
    if not aspects_size.get("ok"):
        print("FAIL aspects size", aspects_size)
        return 9
    for row in aspects_size.get("data") or []:
        if row.get("aspect") != "size":
            print("FAIL aspect filter", row)
            return 10

    bad_aspect = run_tool("get_aspect_stats", {"aspect": "物流"})
    print("get_aspect_stats(非法)", bad_aspect.get("ok"), bad_aspect.get("error"))
    if bad_aspect.get("ok") or bad_aspect.get("error") != "invalid_args":
        print("FAIL expected invalid_args for 物流", bad_aspect)
        return 11

    # --- negative reasons ---
    reasons = run_tool("get_negative_reasons", {"limit": 5})
    print(
        "get_negative_reasons",
        reasons.get("ok"),
        summarize_for_step("get_negative_reasons", reasons),
    )
    if not reasons.get("ok") or not (reasons.get("data") or []):
        print("FAIL reasons", reasons)
        return 12

    sample_asin = (reasons.get("data") or [{}])[0].get("parent_asin")
    if sample_asin:
        filtered = run_tool(
            "get_negative_reasons",
            {"limit": 20, "parent_asin": sample_asin},
        )
        if not filtered.get("ok"):
            print("FAIL reasons filter", filtered)
            return 13
        for row in filtered.get("data") or []:
            if row.get("parent_asin") != sample_asin:
                print("FAIL parent_asin filter", row)
                return 14
        print(
            "get_negative_reasons(filter)",
            "ok",
            summarize_for_step("get_negative_reasons", filtered),
            f"asin={sample_asin}",
        )

    # --- unknown tool ---
    unknown = run_tool("not_a_tool", {})
    print("not_a_tool", unknown.get("ok"), unknown.get("error"))
    if unknown.get("ok") or unknown.get("error") != "unknown_tool":
        print("FAIL expected unknown_tool", unknown)
        return 15

    print("TOOLS_SMOKE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
