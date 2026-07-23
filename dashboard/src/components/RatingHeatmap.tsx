import { useMemo, useState } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { MatrixCell } from "../types";
import { useReducedMotion } from "../hooks/useReducedMotion";
import { ChartView } from "./ChartView";

type Props = { rows: MatrixCell[] };

export function RatingHeatmap({ rows }: Props) {
  const reducedMotion = useReducedMotion();
  const [hovered, setHovered] = useState<[number, number] | null>(null);
  const events = useMemo(
    () => ({
      mouseover: (params: unknown) => {
        const value = (params as { value?: number[] }).value;
        if (Array.isArray(value)) setHovered([value[0], value[1]]);
      },
      globalout: () => setHovered(null),
    }),
    [],
  );
  const option = useMemo<EChartsCoreOption>(() => {
    const ratings = [1, 2, 3, 4, 5];
    const labels = ["negative", "neutral", "positive"];
    const labelZh: Record<string, string> = {
      negative: "预测负面",
      neutral: "预测中性",
      positive: "预测正面",
    };
    const data = rows.map((r) => {
      const value = [
        labels.indexOf(r.pred_label),
        ratings.indexOf(Number(r.rating_value)),
        Number(r.rate_within_rating),
        Number(r.review_count),
      ];
      const related =
        !hovered || value[0] === hovered[0] || value[1] === hovered[1];
      return {
        value,
        itemStyle: { opacity: related ? 1 : 0.3 },
      };
    });
    return {
      animation: !reducedMotion,
      animationDuration: 720,
      animationDelay: (index: number) =>
        reducedMotion ? 0 : Math.floor(index / labels.length) * 90,
      animationEasing: "cubicOut",
      // Keep the x-axis labels and the continuous color legend on separate rows.
      grid: { left: 58, right: 16, top: 10, bottom: 68 },
      tooltip: {
        backgroundColor: "rgba(15, 28, 46, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#f8fafc" },
        formatter: (p: { value: number[] }) => {
          const [xi, yi, v, count] = p.value;
          return `${ratings[yi]}★ × ${labelZh[labels[xi]]}<br/>数量 ${count.toLocaleString()}<br/>占比 ${(v * 100).toFixed(1)}%`;
        },
      },
      xAxis: {
        type: "category",
        data: labels.map((l) => labelZh[l]),
        axisLabel: { color: "#64748b", fontSize: 11, margin: 8 },
      },
      yAxis: {
        type: "category",
        data: ratings.map((r) => `${r}★`),
        axisLabel: { color: "#64748b", fontSize: 11 },
      },
      visualMap: {
        min: 0,
        max: 1,
        dimension: 2,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 4,
        itemWidth: 8,
        itemHeight: 240,
        inRange: { color: ["#ecfdf5", "#0f766e", "#881337"] },
        textStyle: { color: "#64748b", fontSize: 10 },
      },
      series: [
        {
          type: "heatmap",
          data,
          label: {
            show: true,
            formatter: (p: { value: number[] }) =>
              `${(p.value[2] * 100).toFixed(0)}%`,
            fontSize: 10,
            color: "#0f172a",
          },
          emphasis: {
            focus: "self",
            itemStyle: {
              borderColor: "#8eb8ff",
              borderWidth: 2,
              shadowBlur: 12,
              shadowColor: "rgba(76,141,255,0.45)",
            },
          },
          blur: { itemStyle: { opacity: 0.32 } },
        },
      ],
    };
  }, [rows, reducedMotion, hovered]);

  return (
    <ChartView
      option={option}
      className="chart-host chart-host--tall"
      onEvents={events}
    />
  );
}
