"""H2 smoke: orchestrator + DeepSeek on demo script 1.

    set PYTHONPATH=%CD%
    .venv\\Scripts\\python.exe -m agent.scripts.chat_smoke
"""

from __future__ import annotations

import json
import sys

from agent.config import reset_settings_cache
from agent.orchestrator import chat


QUESTION = "当前数据范围内，整体评论情感分布和负面率是多少？"


def main() -> int:
    reset_settings_cache()
    result = chat(QUESTION)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("steps"):
        print("FAIL: steps empty — model did not call tools", file=sys.stderr)
        return 1
    tool_names = [s.get("tool") for s in result["steps"]]
    if "get_kpi" not in tool_names:
        print(f"FAIL: expected get_kpi in steps, got {tool_names}", file=sys.stderr)
        return 2

    answer = result.get("answer") or ""
    if "0" not in answer and "0.0" not in answer and "0%" not in answer:
        print("WARN: answer may miss negative_rate 0 — check manually")

    lowered = answer.lower()
    if "phase_d_e" not in lowered and "烟测" not in answer and "非生产" not in answer and "契约" not in answer and "data_scope" not in lowered:
        print("WARN: answer may miss data_scope / 局限声明 — check manually")

    if result.get("error") and result.get("ok") is False and result.get("error") != "max_steps_exceeded":
        # soft ok if we still have steps+answer
        if not answer:
            print("FAIL:", result.get("error"), file=sys.stderr)
            return 3

    print("CHAT_SMOKE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
