import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { AspectRow } from "../types";
import { aspectLabel } from "../labels";
import { ChartView } from "./ChartView";

type Props = {
  rows: AspectRow[];
};

export function AspectBarChart({ rows }: Props) {
  const option = useMemo<EChartsCoreOption>(() => {
    const grouped = new Map<string, number>();
    for (const row of rows) {
      const key = row.aspect;
      grouped.set(key, (grouped.get(key) || 0) + Number(row.negative_count || 0));
    }
    const entries = [...grouped.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
    const labels = entries.map(([aspect]) => aspectLabel(aspect));
    const values = entries.map(([, count]) => count);

    return {
      grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(15, 28, 46, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#f8fafc", fontFamily: "IBM Plex Sans, sans-serif" },
      },
      xAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "rgba(15, 28, 46, 0.08)" } },
        axisLabel: {
          color: "#64748b",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 11,
        },
      },
      yAxis: {
        type: "category",
        data: labels.reverse(),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: {
          color: "#334155",
          fontFamily: "IBM Plex Sans, sans-serif",
          fontSize: 11,
          width: 120,
          overflow: "truncate",
        },
      },
      series: [
        {
          type: "bar",
          data: values.reverse(),
          barWidth: 14,
          itemStyle: {
            borderRadius: [0, 6, 6, 0],
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: "#0f766e" },
                { offset: 1, color: "#14b8a6" },
              ],
            },
          },
        },
      ],
    };
  }, [rows]);

  return <ChartView option={option} className="chart-host chart-host--tall" />;
}
