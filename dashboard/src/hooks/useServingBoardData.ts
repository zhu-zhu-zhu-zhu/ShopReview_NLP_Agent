import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  clearApiCache,
  fetchAlerts,
  fetchAspects,
  fetchCategories,
  fetchConfidence,
  fetchDailyTrend,
  fetchHealth,
  fetchKpi,
  fetchMonthlyTrend,
  fetchPositiveProducts,
  fetchPositiveStores,
  fetchProducts,
  fetchRatingMatrix,
  fetchReasons,
  fetchSamples,
  fetchStores,
  fetchVerified,
} from "../api";
import type {
  AlertRow,
  AspectRow,
  CategoryRow,
  ConfidenceRow,
  HealthPayload,
  KpiRecord,
  MatrixCell,
  ProductRow,
  ReasonRow,
  SampleRow,
  StoreRow,
  TrendPoint,
  VerifiedRow,
} from "../types";

export type ServingBoardData = {
  health: HealthPayload;
  kpi: KpiRecord;
  products: ProductRow[];
  positiveProducts: ProductRow[];
  aspects: AspectRow[];
  reasons: ReasonRow[];
  daily: TrendPoint[];
  monthly: TrendPoint[];
  alerts: AlertRow[];
  samples: SampleRow[];
  categories: CategoryRow[];
  stores: StoreRow[];
  positiveStores: StoreRow[];
  verified: VerifiedRow[];
  matrix: MatrixCell[];
  confidence: ConfidenceRow[];
};

function unwrap<T>(wrap: { ok: boolean; data: T } | null, fallback: T): T {
  if (wrap?.ok) return wrap.data;
  return fallback;
}

export function useServingBoardData() {
  const [data, setData] = useState<ServingBoardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadedAt, setLoadedAt] = useState("");

  const reload = useCallback(async (force = false) => {
    if (force) clearApiCache();
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all([
        fetchHealth(),
        fetchKpi(),
        fetchProducts(),
        fetchPositiveProducts(),
        fetchAspects(),
        fetchReasons(),
        fetchDailyTrend(),
        fetchMonthlyTrend(),
        fetchAlerts(),
        fetchSamples(),
        fetchCategories(),
        fetchStores(),
        fetchPositiveStores(),
        fetchVerified(),
        fetchRatingMatrix(),
        fetchConfidence(),
      ]);
      const [
        health,
        kpiWrap,
        productsWrap,
        positiveProductsWrap,
        aspectsWrap,
        reasonsWrap,
        dailyWrap,
        monthlyWrap,
        alertsWrap,
        samplesWrap,
        categoriesWrap,
        storesWrap,
        positiveStoresWrap,
        verifiedWrap,
        matrixWrap,
        confidenceWrap,
      ] = results;

      if (
        !kpiWrap.ok ||
        !productsWrap.ok ||
        !positiveProductsWrap.ok ||
        !positiveStoresWrap.ok
      ) {
        throw new Error("核心 KPI / 商品或店铺榜单接口返回 ok=false");
      }

      setData({
        health,
        kpi: kpiWrap.data,
        products: productsWrap.data,
        positiveProducts: positiveProductsWrap.data,
        aspects: unwrap(aspectsWrap, []),
        reasons: unwrap(reasonsWrap, []),
        daily: unwrap(dailyWrap, []),
        monthly: unwrap(monthlyWrap, []),
        alerts: unwrap(alertsWrap, []),
        samples: unwrap(samplesWrap, []),
        categories: unwrap(categoriesWrap, []),
        stores: unwrap(storesWrap, []),
        positiveStores: positiveStoresWrap.data,
        verified: unwrap(verifiedWrap, []),
        matrix: unwrap(matrixWrap, []),
        confidence: unwrap(confidenceWrap, []),
      });
      setLoadedAt(new Date().toLocaleString("zh-CN", { hour12: false }));
    } catch (err) {
      setData(null);
      if (err instanceof ApiError) setError(err.message);
      else if (err instanceof Error) setError(err.message);
      else setError("未知错误");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload(false);
  }, [reload]);

  return { data, error, loading, loadedAt, reload };
}

/** Command-wall health index: higher is healthier. */
export function healthIndex(
  kpi: KpiRecord,
  alertHighCount: number,
  storeNegRates: number[] = [],
): number {
  const base = (1 - Number(kpi.negative_rate || 0)) * 100;
  const alertPenalty = Math.min(15, alertHighCount * 1.1);
  const topStore =
    storeNegRates.length > 0
      ? storeNegRates.slice(0, 3).reduce((a, b) => a + b, 0) /
        Math.min(3, storeNegRates.length)
      : 0;
  const storePenalty = Math.min(12, topStore * 25);
  return Math.max(0, Math.min(100, base - alertPenalty - storePenalty));
}
