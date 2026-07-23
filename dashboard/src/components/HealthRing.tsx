import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { KpiRecord } from "../types";
import { useReducedMotion } from "../hooks/useReducedMotion";
import { AnimatedNumber } from "./AnimatedNumber";
import { ChartView } from "./ChartView";

type Props = {
  kpi: KpiRecord;
  score: number;
  dark?: boolean;
};

export function HealthRing({ score, dark }: Props) {
  const reducedMotion = useReducedMotion();
  const option = useMemo<EChartsCoreOption>(() => {
    return {
      animation: !reducedMotion,
      animationDuration: 1000,
      animationEasing: "cubicOut",
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
              itemStyle: {
                color:
                  score >= 70
                    ? "#14b8a6"
                    : score >= 50
                      ? "#f59e0b"
                      : "#e11d48",
                shadowBlur: reducedMotion ? 0 : 9,
                shadowColor: "rgba(45,212,191,0.34)",
              },
            },
            {
              value: Math.max(0, 100 - score),
              itemStyle: { color: dark ? "rgba(148,163,184,0.15)" : "rgba(15,28,46,0.08)" },
            },
          ],
        },
      ],
    };
  }, [score, dark, reducedMotion]);

  return (
    <div className="health-ring">
      <ChartView option={option} className="chart-host chart-host--ring" />
      <div className="health-ring__label">
        <AnimatedNumber value={score} format={(value) => value.toFixed(0)} />
        <small>健康指数</small>
        <em>前端派生</em>
      </div>
    </div>
  );
}
