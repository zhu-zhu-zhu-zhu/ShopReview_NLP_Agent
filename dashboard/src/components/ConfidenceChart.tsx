import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { ConfidenceRow } from "../types";
import { ChartView } from "./ChartView";

type Props = { rows: ConfidenceRow[] };

export function ConfidenceChart({ rows }: Props) {
  const option = useMemo<EChartsCoreOption>(() => {
    const ordered = [...rows].sort((a, b) => a.bucket_order - b.bucket_order);
    return {
      grid: { left: 40, right: 16, top: 24, bottom: 32, containLabel: true },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 28, 46, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#f8fafc" },
      },
      xAxis: {
        type: "category",
        data: ordered.map((r) => r.bucket_code),
        axisLabel: { color: "#64748b" },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#64748b" },
        splitLine: { lineStyle: { color: "rgba(15,28,46,0.06)" } },
      },
      series: [
        {
          type: "bar",
          data: ordered.map((r) => r.review_count),
          itemStyle: { color: "#0d9488", borderRadius: [6, 6, 0, 0] },
          barMaxWidth: 42,
        },
      ],
    };
  }, [rows]);

  return <ChartView option={option} className="chart-host" />;
}
