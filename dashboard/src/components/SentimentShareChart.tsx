import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import type { KpiRecord } from "../types";
import { ChartView } from "./ChartView";

type Props = {
  kpi: KpiRecord;
};

export function SentimentShareChart({ kpi }: Props) {
  const option = useMemo<EChartsCoreOption>(() => {
    return {
      color: ["#0f766e", "#64748b", "#be123c"],
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(15, 28, 46, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#f8fafc", fontFamily: "IBM Plex Sans, sans-serif" },
        formatter: (params: unknown) => {
          const p = params as { name: string; value: number; percent: number };
          return `${p.name}<br/>${p.value} 条 · ${p.percent.toFixed(1)}%`;
        },
      },
      legend: {
        bottom: 0,
        left: "center",
        itemWidth: 10,
        itemHeight: 10,
        textStyle: {
          color: "#475569",
          fontFamily: "IBM Plex Sans, sans-serif",
          fontSize: 12,
        },
      },
      series: [
        {
          type: "pie",
          radius: ["42%", "68%"],
          center: ["50%", "46%"],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: "#f4f7f9",
            borderWidth: 3,
          },
          label: {
            color: "#0f1c2e",
            fontFamily: "IBM Plex Sans, sans-serif",
            formatter: "{b}\n{d}%",
          },
          data: [
            { name: "正面", value: kpi.positive_count },
            { name: "中性", value: kpi.neutral_count },
            { name: "负面", value: kpi.negative_count },
          ],
        },
      ],
    };
  }, [kpi]);

  return <ChartView option={option} className="chart-host chart-host--tall" />;
}
