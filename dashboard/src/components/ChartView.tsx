import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import {
  BarChart,
  EffectScatterChart,
  HeatmapChart,
  LineChart,
  PieChart,
} from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";

echarts.use([
  PieChart,
  BarChart,
  LineChart,
  HeatmapChart,
  EffectScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

type Props = {
  option: EChartsCoreOption;
  className?: string;
  onEvents?: Record<string, (params: unknown) => void>;
};

export function ChartView({ option, className, onEvents }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.EChartsType | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    let resizeTimer = 0;
    const onResize = () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => chart.resize(), 120);
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      window.clearTimeout(resizeTimer);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: false, lazyUpdate: true });
  }, [option]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !onEvents) return;
    Object.entries(onEvents).forEach(([eventName, handler]) => {
      chart.on(eventName, handler);
    });
    return () => {
      Object.entries(onEvents).forEach(([eventName, handler]) => {
        chart.off(eventName, handler);
      });
    };
  }, [onEvents]);

  return <div ref={ref} className={className ?? "chart-host"} />;
}
