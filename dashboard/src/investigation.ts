import {
  fetchAlerts,
  fetchAspects,
  fetchConfidence,
  fetchDailyTrend,
  fetchKpi,
  fetchProducts,
  fetchRatingMatrix,
  fetchReasons,
  fetchSamples,
  fetchStores,
} from "./api";
import type {
  DashboardTarget,
  EvidenceSource,
  InvestigationKind,
  InvestigationResult,
} from "./agentTypes";
import type {
  AlertRow,
  HealthPayload,
  ResponseMeta,
  Wrapped,
} from "./types";

const pct = (value: number | undefined) =>
  `${(Number(value || 0) * 100).toFixed(1)}%`;

function firstRow<T>(wrap: Wrapped<T[]> | null): Record<string, unknown> {
  return (wrap?.data?.[0] || {}) as Record<string, unknown>;
}

function sourceOf<T>(
  api: string,
  wrap: Wrapped<T> | null,
  health: HealthPayload,
  extractionMethod = "warehouse_aggregate",
): EvidenceSource {
  const rows = Array.isArray(wrap?.data) ? firstRow(wrap as Wrapped<unknown[]>) : {};
  const meta = (wrap?.meta || {}) as ResponseMeta;
  return {
    api,
    source: meta.source || health.source || "warehouse",
    load_batch_id: String(
      rows.load_batch_id || meta.load_batch_id || health.load_batch_id || "—",
    ),
    model_version: String(
      rows.model_version || meta.model_version || health.model_version || "—",
    ),
    extraction_method: String(
      rows.extraction_method ||
        rows.rule_version ||
        meta.extraction_method ||
        extractionMethod,
    ),
    generated_at:
      String(rows.generated_at || meta.generated_at || "") || undefined,
  };
}

function baseResult(
  kind: InvestigationKind,
  question: string,
  target: DashboardTarget,
): InvestigationResult {
  return {
    id: `${kind}-${Date.now()}`,
    title: "ReviewOps 智能风险调查",
    question,
    conclusion: "",
    riskObject: { kind: "全局", id: "prod_v1_100k", name: "当前生产批次" },
    metrics: [],
    alerts: [],
    aspects: [],
    reasons: [],
    samples: [],
    ranking: [],
    sources: [],
    recommendation: [],
    target,
    generatedAt: new Date().toISOString(),
  };
}

function requireWrap<T>(wrap: Wrapped<T> | null, label: string): Wrapped<T> {
  if (!wrap?.ok) throw new Error(`${label} warehouse data empty`);
  return wrap;
}

export function inferInvestigationKind(question: string): InvestigationKind {
  if (/置信|confidence/i.test(question)) return "confidence";
  if (/一星|星级|矩阵|rating/i.test(question)) return "rating";
  if (/趋势|最近一年|变化|trend/i.test(question)) return "trend";
  if (/告警|alert/i.test(question)) return "alerts";
  if (/原因|方面|aspect|reason/i.test(question)) return "reasons";
  if (/店铺|store/i.test(question)) return "store";
  if (/商品|product|asin/i.test(question)) return "product";
  return "summary";
}

export async function runInvestigation(
  kind: InvestigationKind,
  health: HealthPayload,
  questionOverride?: string,
): Promise<InvestigationResult> {
  if (
    !health.ok ||
    health.data_mode !== "warehouse" ||
    !health.production_business_metrics
  ) {
    throw new Error("warehouse data empty：当前不是可用的生产 warehouse 数据源");
  }

  if (kind === "product") {
    const question = questionOverride || "哪个商品风险最高？";
    const [products, alerts, aspects, reasons, samples] = await Promise.all([
      fetchProducts(10, 5),
      fetchAlerts(20),
      fetchAspects(),
      fetchReasons(20),
      fetchSamples(20, "negative"),
    ]);
    const productWrap = requireWrap(products, "商品风险榜");
    const top = productWrap.data[0];
    if (!top) throw new Error("warehouse data empty：商品风险榜为空");
    const result = baseResult(kind, question, "products");
    result.riskObject = {
      kind: "商品",
      id: top.parent_asin,
      name: top.product_title || top.parent_asin,
      detail: `${top.store_name || "未知店铺"} · ${top.main_category || "未分类"}`,
    };
    result.metrics = [
      { label: "负面率", value: pct(top.negative_rate), tone: "negative" },
      { label: "负面评论", value: String(top.negative_count), tone: "negative" },
      { label: "评论量", value: String(top.review_count), tone: "agent" },
      {
        label: "平均置信度",
        value: pct(top.average_prediction_score),
        tone: "agent",
      },
    ];
    result.ranking = productWrap.data.slice(0, 3).map((row) => ({
      id: row.parent_asin,
      name: row.product_title || row.parent_asin,
      value: row.negative_rate,
      count: row.review_count,
    }));
    result.alerts = (alerts?.data || []).filter(
      (row) => row.entity_id === top.parent_asin,
    );
    result.aspects = (aspects?.data || []).slice(0, 5);
    result.reasons = (reasons?.data || []).slice(0, 5);
    result.samples = (samples?.data || []).slice(0, 3);
    result.conclusion = `${top.parent_asin} 在满足最少 5 条评论的商品中负面率最高，为 ${pct(top.negative_rate)}。负面方面、差评原因与评论样例仅作为当前批次的全局背景证据，不归因到该单品。`;
    result.recommendation = [
      "优先核查该 parent_asin 对应商品页面、尺码/材质描述和近期售后反馈。",
      "结合原始业务系统做单品级复核后再采取下架或运营动作。",
    ];
    result.sources = [
      sourceOf("/api/top-negative-products?limit=10&min_reviews=5", products, health),
      sourceOf("/api/alerts?limit=20&alert_level=", alerts, health),
      sourceOf("/api/aspects", aspects, health, "keyword_rules_v1"),
      sourceOf(
        "/api/negative-reasons?limit=20",
        reasons,
        health,
        "keyword_rules_v1",
      ),
      sourceOf(
        "/api/samples?limit=20&pred_label=negative",
        samples,
        health,
        "warehouse_sample_preview",
      ),
    ];
    return result;
  }

  if (kind === "store") {
    const question = questionOverride || "哪个店铺负面率最高？";
    const [stores, alerts] = await Promise.all([
      fetchStores(10, 20),
      fetchAlerts(20),
    ]);
    const storeWrap = requireWrap(stores, "店铺风险榜");
    const top = storeWrap.data[0];
    if (!top) throw new Error("warehouse data empty：店铺风险榜为空");
    const result = baseResult(kind, question, "stores");
    result.riskObject = {
      kind: "店铺",
      id: top.store_key,
      name: top.store_name,
      detail: `${top.product_count} 个商品`,
    };
    result.metrics = [
      { label: "负面率", value: pct(top.negative_rate), tone: "negative" },
      { label: "评论量", value: String(top.review_count), tone: "agent" },
      { label: "商品数", value: String(top.product_count), tone: "agent" },
      {
        label: "平均评分",
        value: Number(top.average_rating || 0).toFixed(2),
        tone: "neutral",
      },
    ];
    result.ranking = storeWrap.data.slice(0, 3).map((row) => ({
      id: row.store_key,
      name: row.store_name,
      value: row.negative_rate,
      count: row.review_count,
    }));
    result.alerts = (alerts?.data || []).filter(
      (row) => row.entity_id === top.store_key,
    );
    result.conclusion = `${top.store_name} 在评论量不少于 20 的店铺中负面率最高，为 ${pct(top.negative_rate)}。`;
    result.recommendation = [
      "按店铺维度复核高负面商品和售后工单。",
      "将店铺级结果作为排查线索，不替代单条评论与订单核验。",
    ];
    result.sources = [
      sourceOf("/api/stores?limit=10&min_reviews=20", stores, health),
      sourceOf("/api/alerts?limit=20&alert_level=", alerts, health),
    ];
    return result;
  }

  if (kind === "alerts") {
    const question = questionOverride || "当前有哪些高等级告警？";
    const [high, critical] = await Promise.all([
      fetchAlerts(20, "HIGH"),
      fetchAlerts(20, "CRITICAL"),
    ]);
    const highRows = high?.data || [];
    const criticalRows = critical?.data || [];
    const rows = [...criticalRows, ...highRows].slice(0, 20);
    const result = baseResult(kind, question, "alerts");
    result.alerts = rows;
    result.metrics = [
      { label: "CRITICAL", value: String(criticalRows.length), tone: "alert" },
      { label: "HIGH", value: String(highRows.length), tone: "alert" },
      { label: "本次证据", value: String(rows.length), tone: "agent" },
    ];
    result.conclusion = rows.length
      ? `当前接口返回 ${criticalRows.length} 条 CRITICAL 和 ${highRows.length} 条 HIGH 告警。`
      : "当前 warehouse 查询未返回 HIGH 或 CRITICAL 告警。";
    result.recommendation = rows.length
      ? ["优先处理 CRITICAL，再按指标偏离程度处理 HIGH 告警。"]
      : ["继续监控告警阈值，无需基于空结果制造风险结论。"];
    result.sources = [
      sourceOf("/api/alerts?limit=20&alert_level=HIGH", high, health),
      sourceOf("/api/alerts?limit=20&alert_level=CRITICAL", critical, health),
    ];
    return result;
  }

  if (kind === "reasons") {
    const question = questionOverride || "最常见的差评原因是什么？";
    const [reasons, aspects, samples] = await Promise.all([
      fetchReasons(20),
      fetchAspects(),
      fetchSamples(20, "negative"),
    ]);
    const reasonRows = requireWrap(reasons, "全局差评原因").data;
    const aspectRows = requireWrap(aspects, "负面方面").data;
    const top = reasonRows[0];
    const result = baseResult(kind, question, "aspects");
    result.reasons = reasonRows.slice(0, 8);
    result.aspects = aspectRows.slice(0, 8);
    result.samples = (samples?.data || []).slice(0, 3);
    result.ranking = reasonRows.slice(0, 3).map((row) => ({
      id: row.reason_code,
      name: row.reason_name,
      value: row.reason_share,
      count: row.reason_count,
    }));
    result.metrics = [
      {
        label: "首要原因",
        value: top?.reason_name || "无数据",
        tone: "negative",
      },
      {
        label: "原因占比",
        value: pct(top?.reason_share),
        tone: "negative",
      },
      {
        label: "规则版本",
        value: "keyword_rules_v1",
        tone: "agent",
      },
    ];
    result.conclusion = top
      ? `全局粒度下最常见的差评原因是“${top.reason_name}”，占比 ${pct(top.reason_share)}。该结果来自 keyword_rules_v1，不是 LLM 抽取，也不能归因到某个商品。`
      : "当前 warehouse 未返回可用的全局差评原因。";
    result.recommendation = [
      "将高频原因用于全局运营排查，再结合具体商品和脱敏评论样例人工复核。",
    ];
    result.sources = [
      sourceOf(
        "/api/negative-reasons?limit=20",
        reasons,
        health,
        "keyword_rules_v1",
      ),
      sourceOf("/api/aspects", aspects, health, "keyword_rules_v1"),
      sourceOf(
        "/api/samples?limit=20&pred_label=negative",
        samples,
        health,
        "warehouse_sample_preview",
      ),
    ];
    return result;
  }

  if (kind === "confidence") {
    const question = questionOverride || "模型置信度怎么样？";
    const confidence = await fetchConfidence();
    const rows = requireWrap(confidence, "模型置信度").data;
    const total = rows.reduce((sum, row) => sum + row.review_count, 0);
    const weighted =
      total > 0
        ? rows.reduce(
            (sum, row) =>
              sum + Number(row.average_prediction_score || 0) * row.review_count,
            0,
          ) / total
        : 0;
    const result = baseResult(kind, question, "confidence");
    result.metrics = [
      { label: "覆盖评论", value: total.toLocaleString(), tone: "agent" },
      { label: "加权平均置信度", value: pct(weighted), tone: "agent" },
      { label: "分桶数", value: String(rows.length), tone: "neutral" },
    ];
    result.ranking = rows.slice(0, 3).map((row) => ({
      id: row.bucket_code,
      name: row.bucket_code,
      value: Number(row.average_prediction_score || 0),
      count: row.review_count,
    }));
    result.conclusion = `置信度接口覆盖 ${total.toLocaleString()} 条评论，加权平均预测分数为 ${pct(weighted)}。`;
    result.recommendation = ["重点抽查低置信度分桶，不把预测概率解释为业务事实。"];
    result.sources = [
      sourceOf("/api/confidence", confidence, health, "model_probability_bucket"),
    ];
    return result;
  }

  if (kind === "trend") {
    const question = questionOverride || "最近一年负面率如何变化？";
    const trend = await fetchDailyTrend(365);
    const rows = requireWrap(trend, "近 365 日趋势").data;
    const first = rows[0];
    const last = rows[rows.length - 1];
    const delta = Number(last?.negative_rate || 0) - Number(first?.negative_rate || 0);
    const result = baseResult(kind, question, "trend");
    result.metrics = [
      { label: "起点负面率", value: pct(first?.negative_rate), tone: "negative" },
      { label: "终点负面率", value: pct(last?.negative_rate), tone: "negative" },
      {
        label: "变化",
        value: `${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)}pp`,
        tone: delta > 0 ? "negative" : "positive",
      },
      { label: "时间点", value: String(rows.length), tone: "agent" },
    ];
    result.conclusion = rows.length
      ? `近 365 日可用区间内，负面率从 ${pct(first?.negative_rate)} 变为 ${pct(last?.negative_rate)}，变化 ${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)} 个百分点。`
      : "当前 warehouse 未返回近一年趋势数据。";
    result.recommendation = ["结合评论量变化判断波动，避免只根据单日比例采取动作。"];
    result.sources = [
      sourceOf("/api/trend?recent_days=365", trend, health, "daily_aggregate"),
    ];
    return result;
  }

  if (kind === "rating") {
    const question = questionOverride || "一星评论和模型预测是否一致？";
    const matrix = await fetchRatingMatrix();
    const rows = requireWrap(matrix, "星级预测矩阵").data;
    const oneStar = rows.filter((row) => Number(row.rating_value) === 1);
    const negative = oneStar.find((row) => row.pred_label === "negative");
    const total = oneStar.reduce((sum, row) => sum + row.review_count, 0);
    const result = baseResult(kind, question, "rating");
    result.metrics = [
      { label: "一星评论", value: total.toLocaleString(), tone: "agent" },
      {
        label: "预测为负面",
        value: negative?.review_count.toLocaleString() || "0",
        tone: "negative",
      },
      {
        label: "一致比例",
        value: pct(negative?.rate_within_rating),
        tone: "agent",
      },
    ];
    result.conclusion = `一星评论共 ${total.toLocaleString()} 条，其中模型预测为负面的比例为 ${pct(negative?.rate_within_rating)}。这里的“一致”仅指星级与预测标签方向一致。`;
    result.recommendation = ["抽查不一致的一星评论，判断文本歧义、讽刺或标签噪声。"];
    result.sources = [
      sourceOf(
        "/api/rating-matrix",
        matrix,
        health,
        "rating_prediction_crosstab",
      ),
    ];
    return result;
  }

  const question = questionOverride || "生成当前批次总结";
  const [kpi, products, stores, alerts, aspects, reasons, samples] =
    await Promise.all([
      fetchKpi(),
      fetchProducts(10, 5),
      fetchStores(10, 20),
      fetchAlerts(20),
      fetchAspects(),
      fetchReasons(20),
      fetchSamples(20, "negative"),
    ]);
  const kpiRow = requireWrap(kpi, "KPI").data;
  const productRows = requireWrap(products, "商品风险榜").data;
  const storeRows = requireWrap(stores, "店铺风险榜").data;
  const result = baseResult(kind, question, "kpi");
  result.metrics = [
    { label: "评论量", value: kpiRow.review_count.toLocaleString(), tone: "agent" },
    { label: "正面率", value: pct(kpiRow.positive_rate), tone: "positive" },
    { label: "中性率", value: pct(kpiRow.neutral_rate), tone: "neutral" },
    { label: "负面率", value: pct(kpiRow.negative_rate), tone: "negative" },
  ];
  result.ranking = productRows.slice(0, 3).map((row) => ({
    id: row.parent_asin,
    name: row.product_title || row.parent_asin,
    value: row.negative_rate,
    count: row.review_count,
  }));
  result.alerts = (alerts?.data || []).slice(0, 5);
  result.aspects = (aspects?.data || []).slice(0, 5);
  result.reasons = (reasons?.data || []).slice(0, 5);
  result.samples = (samples?.data || []).slice(0, 3);
  result.conclusion = `当前生产批次共 ${kpiRow.review_count.toLocaleString()} 条评论，负面率 ${pct(kpiRow.negative_rate)}。最高风险商品为 ${productRows[0]?.parent_asin || "—"}，最高风险店铺为 ${storeRows[0]?.store_name || "—"}。`;
  result.recommendation = [
    "先处理高等级告警，再从最高风险商品与店铺进入人工复核。",
    "方面和全局差评原因仅用作 keyword_rules_v1 规则线索。",
  ];
  result.sources = [
    sourceOf("/api/kpi", kpi, health),
    sourceOf("/api/top-negative-products?limit=10&min_reviews=5", products, health),
    sourceOf("/api/stores?limit=10&min_reviews=20", stores, health),
    sourceOf("/api/alerts?limit=20&alert_level=", alerts, health),
    sourceOf("/api/aspects", aspects, health, "keyword_rules_v1"),
    sourceOf(
      "/api/negative-reasons?limit=20",
      reasons,
      health,
      "keyword_rules_v1",
    ),
    sourceOf(
      "/api/samples?limit=20&pred_label=negative",
      samples,
      health,
      "warehouse_sample_preview",
    ),
  ];
  return result;
}

export function highAlerts(rows: AlertRow[]): AlertRow[] {
  return rows.filter((row) =>
    ["HIGH", "CRITICAL"].includes(String(row.alert_level).toUpperCase()),
  );
}
