"""Read-only connectivity check against MySQL serving layer (v2)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.providers import reset_provider_cache  # noqa: E402
from app.providers.warehouse import WarehouseProvider  # noqa: E402


def main() -> int:
    reset_provider_cache()
    settings = get_settings()
    print(f"DATA_MODE={settings.data_mode}")
    print(f"MYSQL_HOST={settings.mysql_host}:{settings.mysql_port}")
    print(f"MYSQL_DATABASE={settings.mysql_database}")
    print(f"MYSQL_USER={settings.mysql_user}")
    print(
        f"batch={settings.warehouse_load_batch_id} "
        f"model={settings.warehouse_model_version}"
    )
    if settings.mysql_user.strip().lower() == "root":
        print("REFUSING root user")
        return 2
    provider = WarehouseProvider(settings)
    meta = provider.get_health_meta()
    kpi = provider.get_kpi()
    print("health.ok=", meta.get("ok"))
    print("serving_release=", meta.get("serving_release"))
    print("record_counts=", meta.get("record_counts"))
    print(
        "kpi.review_count=",
        kpi.get("review_count"),
        "positive=",
        kpi.get("positive_count"),
        "neutral=",
        kpi.get("neutral_count"),
        "negative=",
        kpi.get("negative_count"),
    )
    aspects = provider.get_aspects(aspect=None)
    print("aspects_n=", len(aspects), "sample=", [a.get("aspect") for a in aspects[:3]])
    reasons = provider.get_negative_reasons(limit=5, parent_asin=None)
    print(
        "reasons_n=",
        len(reasons),
        "sample=",
        [r.get("reason_code") for r in reasons[:3]],
    )
    alerts = provider.get_alerts(limit=3)
    print("alerts_n=", len(alerts), "levels=", [a.get("alert_level") for a in alerts])
    samples = provider.get_samples(limit=3)
    print(
        "samples_n=",
        len(samples),
        "labels=",
        [s.get("pred_label") for s in samples],
    )
    print("PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc
