import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { KpiRecord } from "../types";
import { ChartView } from "./ChartView";

type Props = {
  kpi: KpiRecord;
  score: number;
  dark?: boolean;
};

export function HealthRing({ score, dark }: Props) {
  const option = useMemo<EChartsCoreOption>(() => {
    const ink = dark ? "#e2e8f0" : "#0f172a";
    const muted = dark ? "#94a3b8" : "#64748b";
    return {
      series: [
        {
          type: "pie",
          radius: ["68%", "82%"],
          center: ["50%", "50%"],
          silent: true,
          label: { show: false },
          data: [
            {
              value: score,
              itemStyle: { color: score >= 70 ? "#14b8a6" : score >= 50 ? "#f59e0b" : "#e11d48" },
            },
            {
              value: Math.max(0, 100 - score),
              itemStyle: { color: dark ? "rgba(148,163,184,0.15)" : "rgba(15,28,46,0.08)" },
            },
          ],
        },
        {
          type: "pie",
          radius: ["0%", "58%"],
          center: ["50%", "50%"],
          silent: true,
          label: {
            show: true,
            position: "center",
            formatter: () => `{a|${score.toFixed(0)}}\n{b|健康指数}`,
            rich: {
              a: {
                fontSize: 28,
                fontWeight: 700,
                fontFamily: "IBM Plex Mono, monospace",
                color: ink,
                lineHeight: 32,
              },
              b: { fontSize: 10, color: muted, lineHeight: 16 },
            },
          },
          data: [{ value: 1, itemStyle: { color: "transparent" } }],
        },
      ],
    };
  }, [score, dark]);

  return <ChartView option={option} className="chart-host chart-host--ring" />;
}
