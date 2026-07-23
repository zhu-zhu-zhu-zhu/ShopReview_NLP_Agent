import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { TrendPoint } from "../types";
import { ChartView } from "./ChartView";

type Props = {
  rows: TrendPoint[];
  mode: "daily" | "monthly";
};

export function TrendLineChart({ rows, mode }: Props) {
  const option = useMemo<EChartsCoreOption>(() => {
    const xs = rows.map((r) => (mode === "daily" ? String(r.dt) : String(r.month_id)));
    return {
      grid: { left: 48, right: 24, top: 36, bottom: 48 },
      legend: {
        top: 0,
        textStyle: { color: "#64748b", fontFamily: "IBM Plex Sans, sans-serif" },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 28, 46, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#f8fafc" },
      },
      xAxis: {
        type: "category",
        data: xs,
        axisLabel: {
          color: "#64748b",
          fontSize: 10,
          hideOverlap: true,
        },
        axisLine: { lineStyle: { color: "rgba(15,28,46,0.12)" } },
      },
      yAxis: [
        {
          type: "value",
          name: "评论量",
          axisLabel: { color: "#64748b", fontSize: 10 },
          splitLine: { lineStyle: { color: "rgba(15,28,46,0.06)" } },
        },
        {
          type: "value",
          name: "负面率",
          min: 0,
          max: 1,
          axisLabel: {
            color: "#64748b",
            fontSize: 10,
            formatter: (v: number) => `${Math.round(v * 100)}%`,
          },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "评论量",
          type: "line",
          smooth: true,
          showSymbol: false,
          data: rows.map((r) => r.review_count),
          lineStyle: { width: 2, color: "#0f766e" },
          areaStyle: { color: "rgba(15,118,110,0.12)" },
        },
        {
          name: "负面率",
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          showSymbol: false,
          data: rows.map((r) => r.negative_rate),
          lineStyle: { width: 2, color: "#e11d48" },
        },
      ],
    };
  }, [rows, mode]);

  return <ChartView option={option} className="chart-host chart-host--tall" />;
}
