import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { TrendPoint } from "../types";
import { useReducedMotion } from "../hooks/useReducedMotion";
import { ChartView } from "./ChartView";

type Props = {
  rows: TrendPoint[];
  mode: "daily" | "monthly";
};

export function TrendLineChart({ rows, mode }: Props) {
  const reducedMotion = useReducedMotion();
  const option = useMemo<EChartsCoreOption>(() => {
    const xs = rows.map((r) => (mode === "daily" ? String(r.dt) : String(r.month_id)));
    const latestIndex = rows.reduce(
      (last, row, index) =>
        Number.isFinite(Number(row.negative_rate)) ? index : last,
      -1,
    );
    return {
      color: ["#0f9b8e", "#f31559"],
      animation: !reducedMotion,
      animationDuration: 1050,
      animationDurationUpdate: 760,
      animationEasing: "cubicOut",
      animationEasingUpdate: "cubicOut",
      // Reserve balanced label gutters for the two y-axes inside the card border.
      grid: { left: 58, right: 58, top: 52, bottom: 42 },
      legend: {
        top: 8,
        data: ["评论量", "负面率"],
        itemWidth: 18,
        itemHeight: 8,
        textStyle: { color: "#64748b", fontFamily: "IBM Plex Sans, sans-serif" },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "line",
          lineStyle: {
            color: "rgba(148, 163, 184, 0.45)",
            type: "dashed",
            width: 1,
          },
        },
        backgroundColor: "rgba(15, 28, 46, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#f8fafc" },
      },
      xAxis: {
        type: "category",
        data: xs,
        boundaryGap: false,
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
          nameGap: 18,
          nameTextStyle: { color: "#64748b", fontSize: 10 },
          axisLabel: { color: "#64748b", fontSize: 10, margin: 10 },
          splitLine: { lineStyle: { color: "rgba(15,28,46,0.06)" } },
        },
        {
          type: "value",
          name: "负面率",
          min: 0,
          max: 1,
          nameGap: 18,
          nameTextStyle: { color: "#64748b", fontSize: 10 },
          axisLabel: {
            color: "#64748b",
            fontSize: 10,
            margin: 10,
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
          emphasis: { focus: "series", scale: true },
        },
        {
          name: "负面率",
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          showSymbol: false,
          data: rows.map((r) => r.negative_rate),
          lineStyle: { width: 2, color: "#e11d48" },
          emphasis: { focus: "series", scale: true },
        },
        {
          name: "最新有效点",
          type: "effectScatter",
          yAxisIndex: 1,
          silent: true,
          tooltip: { show: false },
          symbolSize: 7,
          showEffectOn: reducedMotion ? "emphasis" : "render",
          rippleEffect: {
            period: 5,
            scale: 3,
            brushType: "stroke",
          },
          itemStyle: {
            color: "#f31559",
            shadowBlur: reducedMotion ? 0 : 12,
            shadowColor: "rgba(243,21,89,0.55)",
          },
          data:
            latestIndex >= 0
              ? [[xs[latestIndex], rows[latestIndex].negative_rate]]
              : [],
          z: 6,
        },
      ],
    };
  }, [rows, mode, reducedMotion]);

  return <ChartView option={option} className="chart-host chart-host--tall" />;
}
