import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { MatrixCell } from "../types";
import { ChartView } from "./ChartView";

type Props = { rows: MatrixCell[] };

export function RatingHeatmap({ rows }: Props) {
  const option = useMemo<EChartsCoreOption>(() => {
    const ratings = [1, 2, 3, 4, 5];
    const labels = ["negative", "neutral", "positive"];
    const labelZh: Record<string, string> = {
      negative: "预测负面",
      neutral: "预测中性",
      positive: "预测正面",
    };
    const data = rows.map((r) => [
      labels.indexOf(r.pred_label),
      ratings.indexOf(Number(r.rating_value)),
      Number(r.rate_within_rating),
    ]);
    return {
      grid: { left: 72, right: 24, top: 16, bottom: 40 },
      tooltip: {
        backgroundColor: "rgba(15, 28, 46, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#f8fafc" },
        formatter: (p: { data: number[] }) => {
          const [xi, yi, v] = p.data;
          return `${ratings[yi]}★ × ${labelZh[labels[xi]]}<br/>占比 ${(v * 100).toFixed(1)}%`;
        },
      },
      xAxis: {
        type: "category",
        data: labels.map((l) => labelZh[l]),
        axisLabel: { color: "#64748b", fontSize: 11 },
      },
      yAxis: {
        type: "category",
        data: ratings.map((r) => `${r}★`),
        axisLabel: { color: "#64748b", fontSize: 11 },
      },
      visualMap: {
        min: 0,
        max: 1,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        inRange: { color: ["#ecfdf5", "#0f766e", "#881337"] },
        textStyle: { color: "#64748b", fontSize: 10 },
      },
      series: [
        {
          type: "heatmap",
          data,
          label: {
            show: true,
            formatter: (p: { data: number[] }) =>
              `${(p.data[2] * 100).toFixed(0)}%`,
            fontSize: 10,
            color: "#0f172a",
          },
        },
      ],
    };
  }, [rows]);

  return <ChartView option={option} className="chart-host chart-host--tall" />;
}
